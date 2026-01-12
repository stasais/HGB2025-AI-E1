# Exercise 2 - Kafka and Change Data Capture (CDC) Solutions

**Author:** Stanislav Buinitskii  
**Date:** January 12, 2026  
**Course:** Scalable Big Data Systems (HGB2025-AI-E1)

---

## Table of Contents
1. [Activity 1: Debezium CDC Explanation](#activity-1-debezium-cdc-explanation)
2. [Activity 2: Temperature Logging System](#activity-2-temperature-logging-system)
3. [Activity 3: Fraud Detection System](#activity-3-fraud-detection-system)

---

# Activity 1: Debezium CDC Explanation

## What Debezium CDC with PostgreSQL and Kafka Does

**Debezium** is an open-source Change Data Capture (CDC) platform that monitors database transaction logs and streams every data change (INSERT, UPDATE, DELETE) as events to Apache Kafka in near real-time.

### How It Works:

1. **PostgreSQL WAL Monitoring**: Debezium connects to PostgreSQL's Write-Ahead Log (WAL) with logical replication enabled (`wal_level=logical`).

2. **Event Capture**: When a row is inserted/updated/deleted, Debezium reads the change from WAL without impacting database performance.

3. **Kafka Topic Publishing**: Each change is published to a Kafka topic (e.g., `dbserver1.public.activity`) with:
   - **Operation type** (`op`: "c"=create, "u"=update, "d"=delete)
   - **Before/After state** (row data)
   - **Metadata** (timestamp, transaction ID)

4. **Consumer Processing**: Multiple consumers can subscribe independently.

### Why It's Relevant for Big Data in the AI Era

| Benefit | Explanation |
|---------|-------------|
| **Real-Time Streaming** | AI/ML models get fresh data for inference via sub-second propagation |
| **Event-Driven Architecture** | Decouples producers from consumers, enables scalable microservices |
| **Data Lake Ingestion** | Streams changes to data lakes without full table scans |
| **Audit Trail** | Complete history supports GDPR, financial audits |
| **Reduced DB Load** | Reads from logs, minimal impact vs polling |
| **Multi-Consumer** | Multiple AI agents consume same stream independently |

### Use Cases

1. Real-Time Fraud Detection
2. Search Index Synchronization (Elasticsearch)
3. Cache Invalidation (Redis)
4. Data Warehouse ETL (Snowflake/BigQuery)
5. Microservices Event Sourcing
6. ML Feature Stores
7. IoT Analytics

---

# Activity 2: Temperature Logging System

## Scenario
- **Volume**: Low (~1 row/minute)
- **Consumer**: Single script
- **Processing**: Average every 10 minutes

## Part 1: Architecture Choice

### Recommended: Direct PostgreSQL Polling

| Factor | Direct Polling | CDC + Kafka |
|--------|----------------|-------------|
| **Volume** | ✅ Perfect for ~1 msg/min | ❌ Overkill |
| **Complexity** | ✅ Simple SQL | ❌ Kafka + Debezium |
| **Latency** | ✅ 10-min window OK | ❌ Sub-second not needed |
| **Infrastructure** | ✅ Only PostgreSQL | ❌ +3 more components |

**Rationale**: For 1 message/minute with 10-minute processing windows, Kafka is overengineering.

## Part 2: Implementation

Minimal changes to `temperature_data_consumer.py`:

```python
# ADDED lines:
import psycopg2  # PostgreSQL driver

# Database config (same as producer)
DB_NAME = "office_db"
DB_USER = "postgres"  
DB_PASSWORD = "postgrespw"
DB_HOST = "localhost"
DB_PORT = 5432

# Connect to PostgreSQL
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
cursor = conn.cursor()

# Inside loop - query for average:
cursor.execute("""
    SELECT AVG(temperature) FROM temperature_readings 
    WHERE recorded_at >= NOW() - INTERVAL '10 minutes'
""")
result = cursor.fetchone()
avg_temp = result[0] if result[0] else None
```

## Part 3: Architecture Discussion

### Resource Efficiency
- **Compute**: ✅ Minimal - single process, query every 10 min
- **Memory**: ✅ Only aggregated result (~100 bytes)
- **Storage**: ✅ PostgreSQL handles efficiently
- **Network**: ✅ One query per 10 minutes

### Operability
- **Monitoring**: ✅ Standard PostgreSQL + Python logging
- **Debugging**: ✅ SQL testable in psql
- **Deployment**: ✅ Simple - just PostgreSQL + script

### Deployment Complexity
- **Components**: ✅ PostgreSQL + 2 Python scripts
- **Configuration**: ✅ DB credentials only
- **Dependencies**: ✅ Just `psycopg2`

---

# Activity 3: Fraud Detection System

## Scenario
- **Volume**: Very High (100K+ records/second)
- **Consumers**: Multiple independent agents
- **Requirement**: Near real-time alerts

## Part 1: Architecture Choice

### Recommended: Debezium CDC + Kafka

| Requirement | CDC + Kafka Solution |
|-------------|---------------------|
| **100K+ rec/sec** | ✅ Kafka handles millions/sec |
| **Multiple Consumers** | ✅ Consumer groups |
| **Near Real-Time** | ✅ Millisecond latency |
| **Fault Tolerance** | ✅ Kafka replication |
| **Horizontal Scaling** | ✅ Add partitions dynamically |

**Rationale**: Polling 100K/sec would overwhelm PostgreSQL. CDC reads from WAL with minimal impact.

## Part 2: Implementation

### Step 1: Register Debezium Connector

```bash
curl -i -X POST \
  -H "Accept:application/json" \
  -H "Content-Type:application/json" \
  localhost:8083/connectors/ \
  -d '{
    "name": "fraud-transactions-connector",
    "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "database.hostname": "postgres",
      "database.port": "5432",
      "database.user": "postgres",
      "database.password": "postgrespw",
      "database.dbname": "mydb",
      "topic.prefix": "dbserver1",
      "plugin.name": "pgoutput",
      "table.include.list": "public.transactions"
    }
  }'
```

### Step 2: Minimal changes to `fraud_consumer_agent1.py`

```python
# ADDED lines:
import base64  # for decoding Debezium DECIMAL fields
from kafka import KafkaConsumer

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9094']
KAFKA_TOPIC = 'dbserver1.public.transactions'
CONSUMER_GROUP = 'fraud-anomaly-detection'

# Create consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=CONSUMER_GROUP,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Helper to decode Debezium base64-encoded DECIMAL values
def decode_decimal(value, scale=2):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            decoded = base64.b64decode(value)
            int_val = int.from_bytes(decoded, byteorder='big', signed=True)
            return int_val / (10 ** scale)
    return 0.0
```

**Note**: Debezium encodes PostgreSQL DECIMAL/NUMERIC values as base64-encoded bytes. The `decode_decimal()` helper function handles this.

### Step 3: Minimal changes to `fraud_consumer_agent2.py`

```python
# ADDED lines (same pattern):
import base64
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = ['localhost:9094']
KAFKA_TOPIC = 'dbserver1.public.transactions'
CONSUMER_GROUP = 'fraud-velocity-check'  # Different group!

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=CONSUMER_GROUP,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Same decode_decimal() helper function added
```

### Updated `requirements.txt`
```
psycopg2-binary
kafka-python  # ADDED
```

## Part 3: Architecture Discussion

### Resource Efficiency
| Resource | Assessment |
|----------|------------|
| **Compute** | ✅ Kafka brokers efficient; agents minimal CPU |
| **Memory** | ⚠️ Kafka buffers + per-user state |
| **Storage** | ✅ Kafka log compaction |
| **Network** | ⚠️ CDC traffic for every change |

### Operability
| Aspect | Assessment |
|--------|------------|
| **Monitoring** | ✅ Kafka UI, consumer lag |
| **Debugging** | ⚠️ Distributed tracing needed |
| **Alerting** | ✅ Consumer lag alerts |

### Deployment Complexity
| Aspect | Assessment |
|--------|------------|
| **Components** | ⚠️ PostgreSQL + Kafka + Debezium + agents |
| **Configuration** | ⚠️ Connectors, topics, groups |
| **Scaling** | ✅ Add partitions/consumers |

### Performance & Scalability
- **Throughput**: ✅ 100K+ msg/sec
- **Latency**: ✅ <100ms end-to-end
- **Horizontal Scaling**: ✅ Linear with partitions

## Part 4: Comparison with Spark JDBC

| Aspect | CDC + Kafka | Spark JDBC |
|--------|-------------|------------|
| **Data Flow** | Push (event-driven) | Pull (batch) |
| **Latency** | Milliseconds | Minutes |
| **DB Load** | ✅ Minimal (WAL) | ❌ Full scans |
| **Volume** | Only changes | Entire table |
| **Real-time** | ✅ Yes | ❌ No |
| **Infrastructure** | Kafka + Debezium | Spark cluster |

### When to Use Each
| Scenario | Approach |
|----------|----------|
| Real-time fraud detection | CDC + Kafka |
| Batch analytics | Spark JDBC |
| Multiple consumers | CDC + Kafka |
| Complex SQL transforms | Spark JDBC |
| High-frequency changes | CDC + Kafka |

### Conclusion
For fraud detection with 100K+/sec and real-time requirements, **CDC + Kafka is superior**:
- Milliseconds vs minutes latency
- Minimal vs heavy database load
- Native multi-consumer support

---

## Summary

| Activity | Architecture | Rationale |
|----------|--------------|-----------|
| **Activity 2** | PostgreSQL Polling | Low volume, simple, minimal infra |
| **Activity 3** | CDC + Kafka | High volume, real-time, multi-consumer |

---

## Test Results

### Activity 2: Temperature Consumer
```
🌡️ Temperature consumer started. Polling every 10 minutes...
Average temperature last 10 minutes: 27.22 °C
```

### Activity 3: Fraud Detection Agents

**Agent 1 (Anomaly Detection)** - processes 10,000 transactions:
```
🧬 Anomaly Detection Agent started...
📊 Profile updated for User 2137
📊 Profile updated for User 6484
...
🚨 ANOMALY DETECTED: User 2060 spent $6955.90 (Significantly higher than average)
📊 Profile updated for User 3008
...
```

**Agent 2 (Velocity Check)** - processes 10,000 transactions:
```
Agent started. Listening for CDC events...
✅ Transaction OK: 8975 (Score: 0)
✅ Transaction OK: 8980 (Score: 50)  <- High value transaction
✅ Transaction OK: 9638 (Score: 40)  <- Velocity check triggered
...
```

All implementations tested successfully on January 12, 2026.
