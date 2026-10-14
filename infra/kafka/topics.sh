#!/bin/bash
# ============================================================
# Création des topics Kafka pour le Robo-Advisor
# Usage : bash topics.sh <bootstrap-server>
# ============================================================

BOOTSTRAP=${1:-localhost:9092}

echo "=== Création des topics Kafka sur ${BOOTSTRAP} ==="

kafka-topics.sh --bootstrap-server ${BOOTSTRAP} \
  --create --if-not-exists \
  --topic prices-raw \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config max.message.bytes=1048576

kafka-topics.sh --bootstrap-server ${BOOTSTRAP} \
  --create --if-not-exists \
  --topic news-raw \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config max.message.bytes=5242880

echo "=== Topics créés ==="
kafka-topics.sh --bootstrap-server ${BOOTSTRAP} --list
