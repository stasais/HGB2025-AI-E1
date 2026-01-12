# Exercise 2 - Architecture Diagrams

**Author:** Stanislav Buinitskii  
**Course:** Scalable Big Data Systems

This document provides visual architecture diagrams for Activity 2 and Activity 3 using Mermaid.

---

## Activity 2: Temperature Logging System

### Architecture Overview

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_1.png)

### Component Description

| Component | File | Description |
|-----------|------|-------------|
| **Temperature Producer** | `temperature_data_producer.py` | Simulates temperature sensor, generates random readings (15-35°C), inserts to PostgreSQL every minute |
| **PostgreSQL Database** | `docker-compose.yaml` | Stores temperature readings in `office_db.temperature_readings` table |
| **Temperature Consumer** | `temperature_data_consumer.py` | Polls database every 10 minutes, calculates average temperature using SQL `AVG()` |

### Data Flow

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_2.png)

### Why Direct Polling?

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_3.png)

---

## Activity 3: Fraud Detection System

### Architecture Overview

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_4.png)

### Component Description

| Component | File/Container | Description |
|-----------|---------------|-------------|
| **Fraud Producer** | `fraud_data_producer.py` | Generates random financial transactions (user_id, amount, timestamp), inserts to PostgreSQL |
| **PostgreSQL** | `postgres` container | Stores transactions with WAL enabled for CDC |
| **Debezium Connect** | `connect` container | Monitors PostgreSQL WAL, captures INSERT/UPDATE/DELETE events |
| **Kafka Broker** | `kafka` container | Message broker, stores CDC events in topics |
| **Agent 1** | `fraud_consumer_agent1.py` | Anomaly Detection - tracks user spending patterns, flags 3σ outliers |
| **Agent 2** | `fraud_consumer_agent2.py` | Velocity Check - monitors transaction frequency, flags rapid transactions |

### CDC Event Flow

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_5.png)

### Debezium CDC Message Structure

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_6.png)

### Multi-Consumer Architecture

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_7.png)

### Agent 1: Anomaly Detection Logic

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_8.png)

### Agent 2: Velocity Check Logic

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_9.png)

---

## Comparison: Activity 2 vs Activity 3

### Architecture Comparison

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_10.png)

### Decision Matrix

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_11.png)

---

## Docker Infrastructure

### Container Architecture

![Diagram](/home/stas/my_git/HGB2025-AI-E1/Exercise2/diagrams/diagram_12.png)

---

## Summary

| Aspect | Activity 2 | Activity 3 |
|--------|------------|------------|
| **Architecture** | Direct Polling | CDC + Kafka |
| **Components** | 2 (DB + Script) | 5 (DB + Debezium + Kafka + Agents) |
| **Latency** | 10 minutes | Milliseconds |
| **Consumers** | 1 | Multiple |
| **Scalability** | Limited | Horizontal |
| **Use Case** | Low-volume monitoring | High-volume real-time detection |
