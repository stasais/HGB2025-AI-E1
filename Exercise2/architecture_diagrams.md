# Exercise 2 - Architecture Diagrams

**Author:** Stanislav Buinitskii  
**Course:** Scalable Big Data Systems

This document provides visual architecture diagrams for Activity 2 and Activity 3 using Mermaid.

---

## Activity 2: Temperature Logging System

### Architecture Overview

```mermaid
flowchart LR
    subgraph Producer["Temperature Producer"]
        TP["temperature_data_producer.py"]
        SENSOR["Temperature Sensor"]
    end

    subgraph Database["PostgreSQL Database"]
        PG[("office_db")]
        TABLE["temperature_readings table"]
    end

    subgraph Consumer["Temperature Consumer"]
        TC["temperature_data_consumer.py"]
        AVG["Calculate AVG"]
    end

    SENSOR --> TP
    TP -->|"INSERT every 1 min"| PG
    PG --> TABLE
    TC -->|"SELECT AVG every 10 min"| TABLE
    TABLE --> AVG
    AVG --> OUTPUT["Display: Average Temperature"]
```

### Component Description

| Component | File | Description |
|-----------|------|-------------|
| **Temperature Producer** | `temperature_data_producer.py` | Simulates temperature sensor, generates random readings (15-35°C), inserts to PostgreSQL every minute |
| **PostgreSQL Database** | `docker-compose.yaml` | Stores temperature readings in `office_db.temperature_readings` table |
| **Temperature Consumer** | `temperature_data_consumer.py` | Polls database every 10 minutes, calculates average temperature using SQL `AVG()` |

### Data Flow

```mermaid
flowchart TD
    subgraph Step1["Step 1: Data Generation"]
        A["Generate random temperature<br/>15.0 - 35.0 °C"]
    end

    subgraph Step2["Step 2: Data Storage"]
        B[("PostgreSQL<br/>office_db")]
        C["temperature_readings<br/>id, temperature, recorded_at"]
    end

    subgraph Step3["Step 3: Data Processing"]
        D["Query: SELECT AVG temperature<br/>WHERE recorded_at >= NOW - 10min"]
        E["Display average"]
    end

    A -->|"INSERT"| B
    B --> C
    C -->|"Every 10 minutes"| D
    D --> E
```

### Why Direct Polling?

```mermaid
flowchart LR
    subgraph Characteristics["Activity 2 Characteristics"]
        VOL["Low Volume<br/>~1 msg/min"]
        CONS["Single Consumer"]
        LAT["10-min latency OK"]
    end

    subgraph Decision["Architecture Decision"]
        POLL["Direct PostgreSQL Polling"]
    end

    subgraph Benefits["Benefits"]
        SIMPLE["Simple implementation"]
        MINIMAL["Minimal infrastructure"]
        MAINT["Easy maintenance"]
    end

    Characteristics --> Decision
    Decision --> Benefits
```

---

## Activity 3: Fraud Detection System

### Architecture Overview

```mermaid
flowchart TB
    subgraph Producer["Fraud Data Producer"]
        FP["fraud_data_producer.py"]
        TRANS["Generate Transactions"]
    end

    subgraph Database["PostgreSQL Database"]
        PG[("mydb")]
        TBL["transactions table"]
        WAL["Write-Ahead Log"]
    end

    subgraph Debezium["Debezium Connect"]
        DEB["Debezium Connector"]
        CDC["Change Data Capture"]
    end

    subgraph Kafka["Apache Kafka"]
        BROKER["Kafka Broker"]
        TOPIC["dbserver1.public.transactions"]
    end

    subgraph Consumers["Fraud Detection Agents"]
        AG1["Agent 1: Anomaly Detection<br/>fraud_consumer_agent1.py"]
        AG2["Agent 2: Velocity Check<br/>fraud_consumer_agent2.py"]
    end

    TRANS --> FP
    FP -->|"INSERT"| PG
    PG --> TBL
    TBL --> WAL
    WAL -->|"Read changes"| DEB
    DEB --> CDC
    CDC -->|"Publish events"| BROKER
    BROKER --> TOPIC
    TOPIC -->|"Consumer Group 1"| AG1
    TOPIC -->|"Consumer Group 2"| AG2
```

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

```mermaid
flowchart LR
    subgraph Transaction["New Transaction"]
        INSERT["INSERT INTO transactions<br/>user_id=123, amount=5000"]
    end

    subgraph PostgreSQL["PostgreSQL"]
        TABLE["transactions table"]
        WAL["WAL Log Entry"]
    end

    subgraph Debezium["Debezium"]
        READ["Read WAL"]
        TRANSFORM["Transform to JSON"]
    end

    subgraph Kafka["Kafka Topic"]
        MSG["CDC Event Message<br/>op: c, before: null<br/>after: user_id, amount, ts"]
    end

    INSERT --> TABLE
    TABLE --> WAL
    WAL --> READ
    READ --> TRANSFORM
    TRANSFORM --> MSG
```

### Debezium CDC Message Structure

```mermaid
flowchart TD
    subgraph CDCMessage["Debezium CDC Message"]
        PAYLOAD["payload"]
        
        subgraph Before["before"]
            BEF["null for INSERT<br/>previous row for UPDATE"]
        end
        
        subgraph After["after"]
            AFT["id: 1234<br/>user_id: 5678<br/>amount: encoded base64<br/>created_at: timestamp"]
        end
        
        subgraph Operation["op"]
            OP["c = CREATE/INSERT<br/>u = UPDATE<br/>d = DELETE"]
        end
    end

    PAYLOAD --> Before
    PAYLOAD --> After
    PAYLOAD --> Operation
```

### Multi-Consumer Architecture

```mermaid
flowchart TB
    subgraph KafkaTopic["Kafka Topic: dbserver1.public.transactions"]
        P0["Partition 0"]
        P1["Partition 1"]
        P2["Partition 2"]
    end

    subgraph ConsumerGroup1["Consumer Group: fraud-anomaly-detection"]
        AG1["Agent 1<br/>Anomaly Detection"]
    end

    subgraph ConsumerGroup2["Consumer Group: fraud-velocity-check"]
        AG2["Agent 2<br/>Velocity Check"]
    end

    P0 --> AG1
    P1 --> AG1
    P2 --> AG1
    
    P0 --> AG2
    P1 --> AG2
    P2 --> AG2

    note1["Each consumer group gets<br/>ALL messages independently"]
```

### Agent 1: Anomaly Detection Logic

```mermaid
flowchart TD
    START["Receive Transaction"]
    
    GET_HISTORY["Get user spending history"]
    
    CHECK{"Has >= 3<br/>transactions?"}
    
    CALC["Calculate:<br/>average, std deviation"]
    
    ANOMALY{"amount > avg * 3<br/>AND amount > 500?"}
    
    ALERT["ALERT: Anomaly Detected"]
    
    UPDATE["Update user profile<br/>Add to history"]
    
    DONE["Process next message"]

    START --> GET_HISTORY
    GET_HISTORY --> CHECK
    CHECK -->|No| UPDATE
    CHECK -->|Yes| CALC
    CALC --> ANOMALY
    ANOMALY -->|Yes| ALERT
    ANOMALY -->|No| UPDATE
    ALERT --> UPDATE
    UPDATE --> DONE
```

### Agent 2: Velocity Check Logic

```mermaid
flowchart TD
    START["Receive Transaction"]
    
    GET_TIME["Get current timestamp"]
    
    WINDOW["Check transactions in<br/>last 60 seconds"]
    
    VELOCITY["Count = number of<br/>transactions in window"]
    
    SCORE["Calculate fraud score"]
    
    RULE1{"velocity > 5?"}
    ADD40["+40 points"]
    
    RULE2{"amount > 4000?"}
    ADD50["+50 points"]
    
    FINAL{"score > 70?"}
    
    ALERT["HIGH FRAUD ALERT"]
    OK["Transaction OK"]

    START --> GET_TIME
    GET_TIME --> WINDOW
    WINDOW --> VELOCITY
    VELOCITY --> SCORE
    SCORE --> RULE1
    RULE1 -->|Yes| ADD40
    RULE1 -->|No| RULE2
    ADD40 --> RULE2
    RULE2 -->|Yes| ADD50
    RULE2 -->|No| FINAL
    ADD50 --> FINAL
    FINAL -->|Yes| ALERT
    FINAL -->|No| OK
```

---

## Comparison: Activity 2 vs Activity 3

### Architecture Comparison

```mermaid
flowchart TB
    subgraph Activity2["Activity 2: Temperature"]
        direction LR
        A2_PROD["Producer"] --> A2_DB[("PostgreSQL")]
        A2_DB -->|"Direct SQL Query"| A2_CONS["Consumer"]
    end

    subgraph Activity3["Activity 3: Fraud Detection"]
        direction LR
        A3_PROD["Producer"] --> A3_DB[("PostgreSQL")]
        A3_DB --> A3_DEB["Debezium"]
        A3_DEB --> A3_KAFKA["Kafka"]
        A3_KAFKA --> A3_C1["Agent 1"]
        A3_KAFKA --> A3_C2["Agent 2"]
    end
```

### Decision Matrix

```mermaid
flowchart LR
    subgraph Requirements["Check Requirements"]
        VOL{"High Volume?<br/>100K+ msg/sec"}
        MULTI{"Multiple<br/>Consumers?"}
        RT{"Real-time<br/>Required?"}
    end

    subgraph Decision["Architecture Choice"]
        POLL["Direct Polling"]
        CDC["CDC + Kafka"]
    end

    VOL -->|No| POLL
    VOL -->|Yes| CDC
    MULTI -->|Yes| CDC
    RT -->|Yes| CDC
```

---

## Docker Infrastructure

### Container Architecture

```mermaid
flowchart TB
    subgraph DockerCompose["Docker Compose Network"]
        subgraph postgres["postgres:18.1"]
            PG_PORT["Port: 5432"]
            DB1["office_db"]
            DB2["mydb"]
        end

        subgraph kafka["bitnami/kafka"]
            K_INT["Port: 9092 internal"]
            K_EXT["Port: 9094 external"]
        end

        subgraph connect["debezium/connect:2.2"]
            DEB_PORT["Port: 8083"]
            CONNECTOR["PostgreSQL Connector"]
        end

        subgraph kafkaui["kafka-ui"]
            UI_PORT["Port: 8080"]
        end
    end

    subgraph PythonScripts["Python Scripts (Host)"]
        PROD1["temperature_data_producer.py"]
        CONS1["temperature_data_consumer.py"]
        PROD2["fraud_data_producer.py"]
        CONS2["fraud_consumer_agent1.py"]
        CONS3["fraud_consumer_agent2.py"]
    end

    PROD1 -->|"5432"| PG_PORT
    CONS1 -->|"5432"| PG_PORT
    PROD2 -->|"5432"| PG_PORT
    
    postgres --> connect
    connect --> kafka
    
    CONS2 -->|"9094"| K_EXT
    CONS3 -->|"9094"| K_EXT
```

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
