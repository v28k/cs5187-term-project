# PostgreSQL Fuzzing Docker Environment

This directory contains the Docker environment for the A3 PostgreSQL fuzzing project.

The Docker image builds PostgreSQL 18.6 from source with coverage instrumentation enabled.

## 1. Build the Docker image

From this directory:

```
sudo docker build -t a3-pg-fuzzing:stage1 .
```

## 2. Start PostgreSQL

Create a container with the coverage directory mounted:

```
sudo docker run \
  --name a3-pg-test \
  -v "$(pwd)/coverage:/coverage" \
  -d \
  a3-pg-fuzzing:stage1
```

Check that it is running:

```
sudo docker ps
```

## 3. Execute a SQL query

Example:

```
sudo docker exec a3-pg-test psql -d postgres -c "SELECT 42;"
```

The query is executed by the instrumented PostgreSQL server inside the container.

## 4. Collect coverage

After executing queries:

```
sudo docker exec a3-pg-test lcov \
  --capture \
  --directory /opt/postgresql-18.6 \
  --output-file /coverage/coverage.info
```

The coverage report will be available on the host at:

```
coverage/coverage.info
```

## 5. Check coverage summary

```
sudo docker exec a3-pg-test lcov \
  --summary /coverage/coverage.info
```

## 6. Stop and remove the container

```
sudo docker rm -f a3-pg-test
```

## Architecture

```
SQL Query
   |
   v
Docker Container
   |
   v
Instrumented PostgreSQL 18.6
   |
   +----> Query result / error
   |
   +----> .gcda coverage files
              |
              v
            lcov
              |
              v
     coverage/coverage.info
```

## Integration with the fuzzing harness

The intended Stage 1 pipeline is:

```
Random / Mutation Generator
          |
          v
      SQL Query
          |
          v
     executor.py
          |
          v
  Docker PostgreSQL
          |
          +----> SUCCESS / ERROR / CRASH / TIMEOUT
          |
          v
      Coverage Data
```

The Docker container provides the instrumented PostgreSQL environment.

The Python executor is responsible for sending SQL queries to PostgreSQL and recording execution results.

## Important

The current Docker setup is intended for local development and fuzzing experiments.

PostgreSQL uses trust authentication for local connections because this is a controlled development environment.
