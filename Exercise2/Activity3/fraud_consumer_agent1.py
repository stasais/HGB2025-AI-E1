# This agent calculates a running average for each user and flags transactions that are significantly higher than their usual behavior (e.g., $3\sigma$ outliers).

import json
import statistics
import base64  # ADDED: for decoding Debezium DECIMAL fields
from kafka import KafkaConsumer  # ADDED: Kafka consumer for CDC streaming architecture

# Configuration
# ADDED: Kafka configuration for Debezium CDC
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9094']
KAFKA_TOPIC = 'dbserver1.public.transactions'
CONSUMER_GROUP = 'fraud-anomaly-detection'

# ADDED: Create Kafka consumer connected to CDC topic
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=CONSUMER_GROUP,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# In-memory store for user spending patterns
user_spending_profiles = {} 

# ADDED: Helper to decode Debezium base64-encoded DECIMAL values
def decode_decimal(value, scale=2):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            # Debezium encodes DECIMAL as base64 big-endian bytes
            decoded = base64.b64decode(value)
            int_val = int.from_bytes(decoded, byteorder='big', signed=True)
            return int_val / (10 ** scale)
    return 0.0

def analyze_pattern(data):
    user_id = data['user_id']
    amount = decode_decimal(data['amount'])  # CHANGED: use decoder
    
    if user_id not in user_spending_profiles:
        user_spending_profiles[user_id] = []
    
    history = user_spending_profiles[user_id]
    
    # Analyze if transaction is an outlier (Need at least 3 transactions to judge)
    is_anomaly = False
    if len(history) >= 3:
        avg = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0
        
        # If amount is > 3x the average (Simple heuristic)
        if amount > (avg * 3) and amount > 500:
            is_anomaly = True

    # Update profile
    history.append(amount)
    # Keep only last 50 transactions per user for memory efficiency
    if len(history) > 50: history.pop(0)
    
    return is_anomaly

print("🧬 Anomaly Detection Agent started...")

for message in consumer: # ADDED: consumer is now defined above with Kafka connection
    payload = message.value.get('payload', {})
    data = payload.get('after')
    
    if data:
        # Match the variable name here...
        is_fraudulent_pattern = analyze_pattern(data)
        
        # ...with the variable name here
        if is_fraudulent_pattern:
            decoded_amount = decode_decimal(data['amount'])  # ADDED: decode for display
            print(f"🚨 ANOMALY DETECTED: User {data['user_id']} spent ${decoded_amount:.2f} (Significantly higher than average)")
        else:
            print(f"📊 Profile updated for User {data['user_id']}")