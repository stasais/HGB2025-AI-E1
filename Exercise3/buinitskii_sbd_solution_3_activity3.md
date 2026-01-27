# Activity 3 - Monitoring User Experience in Near Real-Time

**Student:** Buinitskii  
**Date:** 27.01.2026

---

## 1. Technical Specification Implementation

### 1.1 Requirements Fulfilled

| Requirement | Implementation |
|-------------|----------------|
| Content contains "crash" | `lower(col("content")).contains("crash")` - case insensitive |
| Severity "High" or "Critical" | `(col("severity") == "High") \| (col("severity") == "Critical")` |
| Group by user_id | `.groupBy(window(...), col("user_id"))` |
| 10-second intervals on event timestamp | `window(col("event_time"), "10 seconds")` tumbling window |
| Output when crash_count > 2 | `.filter(col("crash_count") > 2)` |

### 1.2 Source Code: `spark_crash_monitoring.py`

Key changes from baseline:
1. **Timestamp conversion:** Convert epoch milliseconds to Spark TimestampType for windowing
2. **Filter criteria:** Changed from "vulnerability" + "High" to "crash" + ("High" OR "Critical")
3. **Windowed aggregation:** Added 10-second tumbling window based on event_time
4. **Watermark:** Added 30-second watermark for late data handling
5. **Output filter:** Only emit when crash_count > 2

---

## 2. Late-Arriving Records Discussion

### 2.1 What are Late-Arriving Records?
Records that arrive after their event-time window has already closed. Example: an event with timestamp 14:42:55 arrives at 14:43:10, after the [14:42:50, 14:43:00) window closed.

### 2.2 Solution: Watermarking
```python
.withWatermark("event_time", "30 seconds")
```

**How it works:**
- Watermark = max_event_time - 30 seconds
- Windows are kept open until watermark passes their end time
- Records arriving within 30 seconds of their event time are still processed
- Records arriving after 30 seconds are dropped (too late)

**Trade-off:**
- Longer watermark → more late data accepted → more memory usage
- Shorter watermark → less memory → some late data lost

---

## 3. Scalability Discussion

### 3.1 Horizontal Scaling Capabilities

| Component | Scaling Mechanism |
|-----------|-------------------|
| **Kafka partitions** | More partitions = more parallel consumers |
| **Spark executors** | `--num-executors N` distributes processing |
| **Executor cores** | `--executor-cores N` parallel tasks per executor |

### 3.2 How to Scale

```bash
# Scale for more throughput
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --num-executors 4 \
  --executor-cores 4 \
  --executor-memory 4G \
  --conf "spark.sql.shuffle.partitions=16" \
  /opt/spark-apps/spark_crash_monitoring.py
```

### 3.3 Multi-Machine Scalability
- **Data parallelism:** Each Kafka partition processed by different executor
- **State distribution:** Window state distributed across executors via state store
- **Network overhead:** Shuffle for aggregation is the main bottleneck

---

## 4. Fault Tolerance Discussion

### 4.1 Checkpointing
```python
.config("spark.sql.streaming.checkpointLocation", CHECKPOINT_PATH)
```

**What is saved:**
- Kafka offsets (which messages were processed)
- Aggregation state (current window counts)
- Query progress metadata

### 4.2 Recovery Scenario
1. Worker node fails mid-batch
2. Spark Master detects failure
3. Task rescheduled on another executor
4. State restored from checkpoint
5. Processing continues from last committed offset

### 4.3 Exactly-Once Semantics
- Kafka offsets committed only after batch completes
- Checkpoint ensures no duplicate processing on restart
- State store preserves window aggregations

---

## 5. Performance Report

### 5.1 Run Command
```bash
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --num-executors 2 \
  --executor-cores 4 \
  --executor-memory 4G \
  /opt/spark-apps/spark_crash_monitoring.py
```

### 5.2 Actual Output
```
-------------------------------------------
Batch: 0
-------------------------------------------
+------------------------------------------+---------+-----------+
|Interval                                  |user_id  |crash_count|
+------------------------------------------+---------+-----------+
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1108|3          |
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1116|3          |
|{2026-01-27 20:16:30, 2026-01-27 20:16:40}|user_1167|3          |
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1322|3          |
|{2026-01-27 20:16:40, 2026-01-27 20:16:50}|user_1247|3          |
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1334|3          |
|{2026-01-27 20:16:30, 2026-01-27 20:16:40}|user_1017|3          |
|{2026-01-27 20:16:30, 2026-01-27 20:16:40}|user_1819|3          |
|{2026-01-27 20:16:30, 2026-01-27 20:16:40}|user_1684|3          |
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1019|3          |
|{2026-01-27 20:16:20, 2026-01-27 20:16:30}|user_1027|3          |
|{2026-01-27 20:16:30, 2026-01-27 20:16:40}|user_1285|3          |
|{2026-01-27 20:16:40, 2026-01-27 20:16:50}|user_1266|5          |
+------------------------------------------+---------+-----------+

-------------------------------------------
Batch: 1
-------------------------------------------
+------------------------------------------+---------+-----------+
|Interval                                  |user_id  |crash_count|
+------------------------------------------+---------+-----------+
|{2026-01-27 20:16:50, 2026-01-27 20:17:00}|user_1552|4          |
+------------------------------------------+---------+-----------+
```

### 5.3 Performance Characteristics
- **Input rate:** Matches load generator (~10,000 records/sec)
- **Filtering:** Reduces data to only crash+High/Critical events
- **State size:** Small (only users with crash_count > 2 in active windows)
- **Latency:** ~10-15 seconds (window duration + processing)

---

## 6. Architecture Summary

```
[Kafka: logs topic]
        |
        v
[Spark Structured Streaming]
        |
   [Parse JSON]
        |
   [Convert timestamp to event_time]
        |
   [Filter: crash + High/Critical]
        |
   [Watermark: 30 seconds]
        |
   [Window: 10 seconds tumbling]
        |
   [GroupBy: window + user_id]
        |
   [Count aggregation]
        |
   [Filter: crash_count > 2]
        |
        v
   [Console Output]
```

---

## 7. Conclusion

The implementation satisfies all Activity 3 requirements:
- Filters for "crash" content (case insensitive)
-  Filters for "High" or "Critical" severity
-  Groups by user_id
-  Uses 10-second tumbling windows on event timestamp
-  Outputs only when crash_count > 2
-  Handles late-arriving records via watermarking
-  Supports horizontal scaling via Spark's distributed architecture
-  Provides fault tolerance via checkpointing
