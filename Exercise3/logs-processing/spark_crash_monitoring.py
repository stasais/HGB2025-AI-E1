from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, lower, count, window
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType
from pyspark.sql.functions import from_unixtime  # added - convert timestamp to datetime

# 1. Configuration & Session Setup
CHECKPOINT_PATH = "/tmp/spark-checkpoints/crash-monitoring"  # added - separate checkpoint for this app

spark = (
    SparkSession.builder
    .appName("CrashMonitoring")  # added - descriptive app name
    .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_PATH)
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

# 2. Define schema
schema = StructType([
    StructField("timestamp", LongType()), 
    StructField("status", StringType()),
    StructField("severity", StringType()),
    StructField("source_ip", StringType()),
    StructField("user_id", StringType()),
    StructField("content", StringType())
])

# 3. Read Stream
raw_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "logs")
    .option("startingOffsets", "earliest")
    .option("failOnDataLoss", "false")
    .load()
)

# 4. Processing, Filtering & Windowed Aggregation for Activity 3
# added - parse JSON and convert timestamp to datetime for windowing
parsed_df = (
    raw_df.select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
    .withColumn("event_time", from_unixtime(col("timestamp") / 1000).cast(TimestampType()))  # added - convert epoch ms to timestamp
)

# added - filter for crash events with High or Critical severity
crash_df = parsed_df.filter(
    (lower(col("content")).contains("crash")) &  # added - case insensitive crash detection
    ((col("severity") == "High") | (col("severity") == "Critical"))  # added - High OR Critical severity
)

# added - 10-second tumbling window aggregation by user_id based on event_time
windowed_df = (
    crash_df
    .withWatermark("event_time", "30 seconds")  # added - watermark for late data handling (30s grace period)
    .groupBy(
        window(col("event_time"), "10 seconds"),  # added - 10-second tumbling window on event timestamp
        col("user_id")
    )
    .agg(count("*").alias("crash_count"))
    .filter(col("crash_count") > 2)  # added - only output when crash_count > 2
    .select(
        col("window").alias("Interval"),  # added - rename for output format
        col("user_id"),
        col("crash_count")
    )
)

# 5. Writing - use update mode for windowed aggregation
query = (
    windowed_df.writeStream
    .outputMode("update")  # added - update mode works with watermark for windowed aggregations
    .format("console")
    .option("truncate", "false")
    .start()
)

query.awaitTermination()
