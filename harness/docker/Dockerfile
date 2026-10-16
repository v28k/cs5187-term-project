# Instrumented PostgreSQL for fuzzing.
#
#   docker build -t pgfuzz:master .                                   # assert-enabled master (bug hunting)
#   docker build -t pgfuzz:18-cov --build-arg PG_REF=REL_18_STABLE --build-arg COVERAGE=1 .   # experiments
#   docker build -t pgfuzz:master-asan --build-arg SANITIZER=asan .  # AddressSanitizer
#
# Build arguments:
#   PG_REF     git branch or tag (master, REL_18_STABLE, REL_18_1, ...)
#   CASSERT    1 = --enable-cassert: Assert() failures abort the backend and print "TRAP:" + a backtrace
#   COVERAGE   1 = --enable-coverage: gcov counters for lcov (about 2x slower)
#   SANITIZER  none | asan | ubsan
#
# The server log is written to /logs/postgresql.log; mount /logs to read it from
# the host (the fuzzer's oracle needs it to see TRAP / PANIC / signal lines).
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git ca-certificates bison flex perl pkg-config \
        libreadline-dev zlib1g-dev libssl-dev libxml2-dev libxslt1-dev libicu-dev liblz4-dev libzstd-dev \
        lcov gdb python3 procps less \
    && rm -rf /var/lib/apt/lists/*

ARG PG_REPO=https://github.com/postgres/postgres.git
ARG PG_REF=master
ARG CASSERT=1
ARG COVERAGE=0
ARG SANITIZER=none

RUN git clone --depth 1 --branch "${PG_REF}" "${PG_REPO}" /opt/postgres \
    && git -C /opt/postgres rev-parse HEAD > /opt/SOURCE_COMMIT

WORKDIR /opt/postgres
RUN set -eux; \
    CFLAGS="-O1 -g -fno-omit-frame-pointer"; LDFLAGS=""; \
    EXTRA="--enable-debug --with-libxml --with-icu --with-lz4 --with-zstd --with-openssl"; \
    [ "$CASSERT" = 1 ] && EXTRA="$EXTRA --enable-cassert"; \
    [ "$COVERAGE" = 1 ] && EXTRA="$EXTRA --enable-coverage" && CFLAGS="-O0 -g"; \
    case "$SANITIZER" in \
      asan)  CFLAGS="$CFLAGS -fsanitize=address"; LDFLAGS="-fsanitize=address" ;; \
      ubsan) CFLAGS="$CFLAGS -fsanitize=undefined -fno-sanitize-recover=all -fno-sanitize=alignment"; LDFLAGS="-fsanitize=undefined" ;; \
    esac; \
    CFLAGS="$CFLAGS" LDFLAGS="$LDFLAGS" ./configure --prefix=/opt/pg $EXTRA > /opt/configure.log; \
    make -j"$(nproc)" world-bin > /opt/make.log 2>&1 || (tail -50 /opt/make.log; exit 1); \
    make install-world-bin >> /opt/make.log 2>&1; \
    /opt/pg/bin/pg_config --configure > /opt/CONFIGURE_FLAGS

RUN useradd -m postgres \
    && mkdir -p /var/lib/postgresql/data /logs /opt/fuzz \
    && chown -R postgres:postgres /var/lib/postgresql /logs /opt/postgres

COPY entrypoint.sh coverage.sh gdb_backtrace.sh postgresql.fuzz.conf /opt/fuzz/
RUN sed -i 's/\r$//' /opt/fuzz/*.sh /opt/fuzz/*.conf && chmod 755 /opt/fuzz/*.sh

ENV PATH="/opt/pg/bin:$PATH" \
    PGDATA=/var/lib/postgresql/data \
    ASAN_OPTIONS="detect_leaks=0:abort_on_error=1:disable_coredump=0:print_stacktrace=1" \
    UBSAN_OPTIONS="print_stacktrace=1"

USER postgres
EXPOSE 5432
VOLUME ["/logs"]
ENTRYPOINT ["/opt/fuzz/entrypoint.sh"]
