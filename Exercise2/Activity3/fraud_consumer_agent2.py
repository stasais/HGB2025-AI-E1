#This agent uses a sliding window (simulated) to perform velocity checks and score the transaction
import json
import base64  # ADDED: for decoding Debezium DECIMAL fields
from collections import deque
import time
from kafka import KafkaConsumer  # ADDED: Kafka consumer for CDC streaming architecture

# ADDED: Kafka configuration for Debezium CDC
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9094']
KAFKA_TOPIC = 'dbserver1.public.transactions'
CONSUMER_GROUP = 'fraud-velocity-check'

# ADDED: Create Kafka consumer connected to CDC topic
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=CONSUMER_GROUP,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Simulated In-Memory State for Velocity Checks.
user_history = {} 

# ADDED: Helper to decode Debezium base64-encoded DECIMAL values
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

def analyze_fraud(transaction):
    user_id = transaction['user_id']
    amount = decode_decimal(transaction['amount'])  # CHANGED: use decoder
    
    # 1. Velocity Check (Recent transaction count)
    now = time.time()
    if user_id not in user_history:
        user_history[user_id] = deque()
    
    # Keep only last 60 seconds of history
    user_history[user_id].append(now)
    while user_history[user_id] and user_history[user_id][0] < now - 60:
        user_history[user_id].popleft()

    velocity = len(user_history[user_id])
    
    # 2. Heuristic Fraud Scoring
    score = 0
    if velocity > 5: score += 40  # Too many transactions in a minute
    if amount > 4000: score += 50 # High value transaction
    
    # 3. Simulate ML Model Hand-off
    # model.predict([[velocity, amount]])
    
    return score

print("Agent started. Listening for CDC events...")
for message in consumer:  # ADDED: consumer is now defined above with Kafka connection
    # Debezium wraps data in an 'after' block
    payload = message.value.get('payload', {})
    data = payload.get('after')
    
    if data:
        fraud_score = analyze_fraud(data)
        if fraud_score > 70:
            decoded_amount = decode_decimal(data['amount'])  # ADDED: decode for display
            print(f"⚠️ HIGH FRAUD ALERT: User {data['user_id']} | Score: {fraud_score} | Amt: ${decoded_amount:.2f}")
        else:
            print(f"✅ Transaction OK: {data['id']} (Score: {fraud_score})")