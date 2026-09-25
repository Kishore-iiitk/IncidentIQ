import os
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SyntheticGenerator")

# 10 realistic multimodal incident scenarios as specified in the architecture
SYNTHETIC_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "SYNTH-INC-001",
        "title": "PostgreSQL connection pool exhaustion",
        "description": "Checkout service experiencing cascading connection timeouts. Max client connections (100) reached on primary PostgreSQL node.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "Database",
        "affected_systems": ["checkout-service", "postgres-primary-node-1", "order-api"],
        "assignment_team": "Database",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-20T10:00:00Z",
        "updated_at": "2026-03-20T11:15:00Z",
        "resolved_at": "2026-03-20T11:15:00Z",
        "confidence": 0.95,
        "root_cause": "A leaking database connection in the checkout retry interceptor caused connection pool saturation, exhausting the server max_connections limit.",
        "recommended_solution": "Deploy hotfix closing unhandled connection leaks in retry handler; increase max_connections to 300; verify connection pool metrics in Grafana.",
        "executive_summary": "P1 Database outage on 2026-03-20 affecting checkout and payment flows for 75 minutes. Root cause was connection leak in retry interceptor. Mitigated by connection purging and connection pool enlargement.",
        "bug_report": {
            "title": "Database connection leak in CheckoutRetryInterceptor",
            "summary": "CheckoutRetryInterceptor fails to close JDBC/async connections on timeout exceptions.",
            "environment": "Production US-East-1",
            "steps_to_reproduce": ["Trigger upstream 504 timeout during checkout", "Observe active DB connections count increment without release"],
            "expected_behavior": "Connection returned to pool on all failure conditions",
            "actual_behavior": "Connection retained in IDLE state until pool starvation occurs",
            "severity": "P1",
            "suspected_component": "checkout-service:db-pool"
        },
        "timeline": [
            {"timestamp": "2026-03-20T10:00:00Z", "event": "Grafana alert: postgresql_active_connections > 95%", "is_approximate": False},
            {"timestamp": "2026-03-20T10:05:00Z", "event": "Customer checkout HTTP 500 error spike detected", "is_approximate": False},
            {"timestamp": "2026-03-20T10:30:00Z", "event": "On-call Database engineer paged and joins incident bridge", "is_approximate": False},
            {"timestamp": "2026-03-20T11:00:00Z", "event": "Hotfix deployed to kill idle connections and patch pool wrapper", "is_approximate": False},
            {"timestamp": "2026-03-20T11:15:00Z", "event": "All checkout services recovered and error rate dropped to 0%", "is_approximate": False}
        ],
        "metadata": {
            "is_synthetic": True,
            "evidence_references": {
                "logs": "data/synthetic/logs/db_pool_exhaustion.log",
                "screenshot": "data/synthetic/screenshots/postgres_pool_spike.png",
                "email": "data/synthetic/emails/db_failure_alert.eml",
                "complaint": "data/synthetic/complaints/checkout_failure_tickets.json",
                "voice_transcript": "On-call DB engineer notes: We are seeing max connections hit on primary. PgBouncer buffer is completely saturated."
            }
        }
    },
    {
        "id": "SYNTH-INC-002",
        "title": "API latency spike on /api/v1/orders",
        "description": "p99 latency escalated from 85ms to 14,200ms following high query volume on unindexed customer order search endpoint.",
        "status": "Resolved",
        "severity": "P2",
        "priority": "P2",
        "category": "Backend",
        "affected_systems": ["orders-api", "elastic-search-proxy", "api-gateway"],
        "assignment_team": "Backend",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-20T12:30:00Z",
        "updated_at": "2026-03-20T13:40:00Z",
        "resolved_at": "2026-03-20T13:40:00Z",
        "confidence": 0.92,
        "root_cause": "Full table scan triggered on orders table due to missing composite index on (tenant_id, created_at).",
        "recommended_solution": "Add concurrent index on orders(tenant_id, created_at); add circuit breaker on order search queries taking > 2000ms.",
        "executive_summary": "P2 Backend performance degradation on orders endpoint. Resolved by adding missing composite database index and tuning query timeouts.",
        "bug_report": {
            "title": "Missing index on orders table causing sequential scan under high load",
            "summary": "Order query performs SEQ SCAN when tenant_id and date range filters are combined.",
            "environment": "Production Multi-Region",
            "steps_to_reproduce": ["GET /api/v1/orders?tenant_id=XYZ&from=2026-01-01", "Check EXPLAIN ANALYZE execution plan"],
            "expected_behavior": "Index scan under 50ms",
            "actual_behavior": "Seq scan taking up to 14 seconds",
            "severity": "P2",
            "suspected_component": "orders-service"
        },
        "timeline": [
            {"timestamp": "2026-03-20T12:30:00Z", "event": "APM p99 latency threshold breached (14.2s)", "is_approximate": False},
            {"timestamp": "2026-03-20T13:10:00Z", "event": "DB query profiler identified unindexed SELECT queries", "is_approximate": False},
            {"timestamp": "2026-03-20T13:35:00Z", "event": "CREATE INDEX CONCURRENTLY completed", "is_approximate": False},
            {"timestamp": "2026-03-20T13:40:00Z", "event": "Latency normalized to 45ms", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-003",
        "title": "Kubernetes pod crash loop in ingress-controller",
        "description": "Ingress controller pods cycling in CrashLoopBackOff with OOMKilled (Exit Code 137). Inbound traffic dropping.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "DevOps",
        "affected_systems": ["k8s-ingress-controller", "nginx-ingress", "edge-router"],
        "assignment_team": "DevOps",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-21T04:10:00Z",
        "updated_at": "2026-03-21T05:00:00Z",
        "resolved_at": "2026-03-21T05:00:00Z",
        "confidence": 0.94,
        "root_cause": "Ingress controller memory limit was set to 512Mi, insufficient for sudden SSL session renegotiation burst.",
        "recommended_solution": "Increase pod memory limit to 2Gi; set HPA minimum replica count to 4.",
        "executive_summary": "P1 Ingress controller failure due to OOMKilled. Ingress availability restored by scaling pod resources.",
        "bug_report": {
            "title": "Ingress controller OOMKilled during TLS handshake spike",
            "summary": "Pods exceed 512Mi memory request during TLS burst.",
            "environment": "EKS Cluster Prod-East",
            "steps_to_reproduce": ["Simulate 50k concurrent TLS handshakes", "Check pod status: CrashLoopBackOff"],
            "expected_behavior": "Autoscale pods smoothly",
            "actual_behavior": "Pods killed with SIGKILL (137)",
            "severity": "P1",
            "suspected_component": "k8s-ingress"
        },
        "timeline": [
            {"timestamp": "2026-03-21T04:10:00Z", "event": "Pod CrashLoopBackOff alert fired", "is_approximate": False},
            {"timestamp": "2026-03-21T04:45:00Z", "event": "Resource quota updated and pods rolled out", "is_approximate": False},
            {"timestamp": "2026-03-21T05:00:00Z", "event": "All ingress pods healthy and ready", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-004",
        "title": "Disk space exhaustion on /var/log volume",
        "description": "App worker instance app-04 disk usage reached 99.8%. Write I/O blocked, application hanging on logging statements.",
        "status": "Resolved",
        "severity": "P2",
        "priority": "P2",
        "category": "Infrastructure",
        "affected_systems": ["app-node-04", "logrotate", "worker-daemon"],
        "assignment_team": "Infrastructure",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-21T08:00:00Z",
        "updated_at": "2026-03-21T08:45:00Z",
        "resolved_at": "2026-03-21T08:45:00Z",
        "confidence": 0.96,
        "root_cause": "A runaway debug logging loop in custom logging appender generated 80GB of uncompressed logs in 3 hours.",
        "recommended_solution": "Purge uncompressed debug logs; correct log level to INFO; enforce daily logrotate maxsize 100M.",
        "executive_summary": "P2 Disk space exhaustion on worker node 04 mitigated by cleaning orphaned logs and enforcing logrotate policies.",
        "bug_report": {
            "title": "Debug logging loop fills disk volume",
            "summary": "Infinite retry logging generates 80GB logs rapidly.",
            "environment": "Production Worker Fleet",
            "steps_to_reproduce": ["Simulate external webhook failure with DEBUG log level enabled"],
            "expected_behavior": "Rate-limited log output",
            "actual_behavior": "Disk capacity saturated in hours",
            "severity": "P2",
            "suspected_component": "logging-agent"
        },
        "timeline": [
            {"timestamp": "2026-03-21T08:00:00Z", "event": "Node disk space alert (> 95%)", "is_approximate": False},
            {"timestamp": "2026-03-21T08:30:00Z", "event": "Orphaned log files cleared via automated script", "is_approximate": False},
            {"timestamp": "2026-03-21T08:45:00Z", "event": "Disk utilization down to 24%", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-005",
        "title": "Authentication failure spike after OAuth token rotation",
        "description": "Users receiving HTTP 401 Unauthorized across web and mobile apps. Internal signing key mismatch.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "Security",
        "affected_systems": ["auth-service", "jwt-verifier", "api-gateway"],
        "assignment_team": "Security",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-21T14:00:00Z",
        "updated_at": "2026-03-21T14:45:00Z",
        "resolved_at": "2026-03-21T14:45:00Z",
        "confidence": 0.98,
        "root_cause": "Automated KMS key rotation updated the public key endpoint before cache expiration on backend verifiers.",
        "recommended_solution": "Synchronize JWKS cache TTL with rotation lead time; refresh JWKS caches across all gateway instances.",
        "executive_summary": "P1 authentication outage. Resolved by manually invalidating stale public key caches on API gateways.",
        "bug_report": {
            "title": "JWKS cache stale during automated KMS key rotation",
            "summary": "Backend verifiers reject newly minted tokens due to cached previous public key.",
            "environment": "Auth Gateway Prod",
            "steps_to_reproduce": ["Rotate KMS signing key", "Issue new JWT", "Validate on cached gateway"],
            "expected_behavior": "Gateway fetches updated JWKS on signature failure",
            "actual_behavior": "Gateway rejects token with 401 until cache TTL expires",
            "severity": "P1",
            "suspected_component": "auth-service:jwks-cache"
        },
        "timeline": [
            {"timestamp": "2026-03-21T14:00:00Z", "event": "401 Unauthorized rate jumped to 68%", "is_approximate": False},
            {"timestamp": "2026-03-21T14:30:00Z", "event": "Flushed Redis JWKS cache across API gateways", "is_approximate": False},
            {"timestamp": "2026-03-21T14:45:00Z", "event": "Token verification restored to 100% success", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-006",
        "title": "Cross-AZ network route flap and packet loss",
        "description": "Cross-availability-zone latency increased with 22% packet loss between us-east-1a and us-east-1b.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "Network",
        "affected_systems": ["transit-gateway", "vpc-peering", "cross-az-link"],
        "assignment_team": "Network",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-22T02:00:00Z",
        "updated_at": "2026-03-22T03:10:00Z",
        "resolved_at": "2026-03-22T03:10:00Z",
        "confidence": 0.90,
        "root_cause": "Faulty physical fiber switch in cloud provider availability zone causing BGP route flaps.",
        "recommended_solution": "Reroute inter-AZ traffic away from degraded transit link; coordinate maintenance with provider.",
        "executive_summary": "P1 inter-AZ packet loss mitigated by rerouting traffic through secondary Direct Connect circuit.",
        "bug_report": {
            "title": "BGP route flap causing severe inter-AZ packet drops",
            "summary": "Transit gateway flapping between primary and backup routes every 12 seconds.",
            "environment": "AWS us-east-1",
            "steps_to_reproduce": ["Send continuous ICMP and TCP traffic across VPC peering"],
            "expected_behavior": "0% packet loss, <2ms latency",
            "actual_behavior": "22% packet loss during flap intervals",
            "severity": "P1",
            "suspected_component": "network:tgw"
        },
        "timeline": [
            {"timestamp": "2026-03-22T02:00:00Z", "event": "Cross-AZ ping loss alert triggered", "is_approximate": False},
            {"timestamp": "2026-03-22T02:40:00Z", "event": "Traffic manually shifted to backup transit gateway", "is_approximate": False},
            {"timestamp": "2026-03-22T03:10:00Z", "event": "0% packet loss confirmed across all zones", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-007",
        "title": "Deployment failure due to incompatible DB schema migration",
        "description": "Canary deployment of release v3.8.0 failed. New code expected column 'user_tier' which had not yet migrated.",
        "status": "Resolved",
        "severity": "P2",
        "priority": "P2",
        "category": "DevOps",
        "affected_systems": ["ci-cd-pipeline", "argocd", "user-service"],
        "assignment_team": "DevOps",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-22T11:00:00Z",
        "updated_at": "2026-03-22T11:35:00Z",
        "resolved_at": "2026-03-22T11:35:00Z",
        "confidence": 0.97,
        "root_cause": "Migration step was ordered after application rollout in deployment manifest instead of pre-sync hook.",
        "recommended_solution": "Rollback canary deployment; adjust ArgoCD hook to PreSync for database schema migrations.",
        "executive_summary": "P2 deployment failure safely contained to 5% canary users. Rollback completed within 35 minutes.",
        "bug_report": {
            "title": "Database migration out of sync with application rollout",
            "summary": "Application pods started before database migrations completed.",
            "environment": "Prod Canary",
            "steps_to_reproduce": ["Deploy application requiring new schema column without running migration first"],
            "expected_behavior": "PreSync migration runs and validates before pod launch",
            "actual_behavior": "Pods launched and crashed with ColumnNotFound error",
            "severity": "P2",
            "suspected_component": "deploy-pipeline"
        },
        "timeline": [
            {"timestamp": "2026-03-22T11:00:00Z", "event": "ArgoCD canary deploy triggered", "is_approximate": False},
            {"timestamp": "2026-03-22T11:05:00Z", "event": "Canary pods failing health checks", "is_approximate": False},
            {"timestamp": "2026-03-22T11:20:00Z", "event": "Automated rollback triggered by canary analysis", "is_approximate": False},
            {"timestamp": "2026-03-22T11:35:00Z", "event": "Canary rollback verified; all traffic on stable v3.7.9", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-008",
        "title": "Memory leak in Java payment gateway service",
        "description": "JVM heap memory steadily climbed to 98% over 18 hours until full GC pauses locked request processing.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "Backend",
        "affected_systems": ["payment-gateway", "jvm-runtime", "payment-db"],
        "assignment_team": "Backend",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-22T17:00:00Z",
        "updated_at": "2026-03-22T18:15:00Z",
        "resolved_at": "2026-03-22T18:15:00Z",
        "confidence": 0.93,
        "root_cause": "ThreadLocal context objects were not removed in payment audit filter, causing classloader memory retention.",
        "recommended_solution": "Invoke ThreadLocal.remove() in finally block of audit filter; trigger rolling pod restarts.",
        "executive_summary": "P1 payment gateway memory leak resolved by deploying fix for ThreadLocal leak and restarting JVM workers.",
        "bug_report": {
            "title": "ThreadLocal leak in PaymentAuditFilter causes OutOfMemoryError",
            "summary": "Audit context objects accumulate in ThreadLocalMap without cleanup.",
            "environment": "Prod Payment Cluster",
            "steps_to_reproduce": ["Send 100k requests through PaymentAuditFilter", "Observe heap dump showing ThreadLocalMap growth"],
            "expected_behavior": "ThreadLocal context cleared after each request",
            "actual_behavior": "Objects retained indefinitely in worker threads",
            "severity": "P1",
            "suspected_component": "payment-gateway:audit-filter"
        },
        "timeline": [
            {"timestamp": "2026-03-22T17:00:00Z", "event": "Long GC pause (> 5000ms) alerts triggered", "is_approximate": False},
            {"timestamp": "2026-03-22T17:35:00Z", "event": "Heap dump extracted and ThreadLocal leak identified", "is_approximate": False},
            {"timestamp": "2026-03-22T18:00:00Z", "event": "Hotfix deployed to prod cluster", "is_approximate": False},
            {"timestamp": "2026-03-22T18:15:00Z", "event": "JVM memory stable at 38% after restart", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-009",
        "title": "Redis cluster maxmemory OOM command rejection",
        "description": "Redis cluster returned 'OOM command not allowed when used memory > maxmemory' error on session writes.",
        "status": "Resolved",
        "severity": "P2",
        "priority": "P2",
        "category": "Database",
        "affected_systems": ["redis-cache-cluster", "session-manager", "user-web"],
        "assignment_team": "Database",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-23T06:00:00Z",
        "updated_at": "2026-03-23T06:45:00Z",
        "resolved_at": "2026-03-23T06:45:00Z",
        "confidence": 0.95,
        "root_cause": "Session keys were set without TTL during anonymous visitor tracking feature rollout, bypassing LRU eviction.",
        "recommended_solution": "Set mandatory 24-hour TTL on anonymous tracking keys; dynamically adjust maxmemory-policy to allkeys-lru.",
        "executive_summary": "P2 Redis session storage exhaustion resolved by switching eviction policy to allkeys-lru and enforcing TTL.",
        "bug_report": {
            "title": "Anonymous visitor session keys created without TTL",
            "summary": "SET commands omitted EX argument, preventing automatic expiration.",
            "environment": "Prod Redis Cluster",
            "steps_to_reproduce": ["Browse as unauthenticated user", "Check TTL of session key in Redis: returns -1 (no expire)"],
            "expected_behavior": "Keys expire after 86400 seconds",
            "actual_behavior": "Keys persist forever until memory exhausted",
            "severity": "P2",
            "suspected_component": "session-service:redis"
        },
        "timeline": [
            {"timestamp": "2026-03-23T06:00:00Z", "event": "Redis OOM errors reported by session manager", "is_approximate": False},
            {"timestamp": "2026-03-23T06:20:00Z", "event": "Config maxmemory-policy changed to allkeys-lru", "is_approximate": False},
            {"timestamp": "2026-03-23T06:45:00Z", "event": "Memory dropped from 100% to 62%", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    },
    {
        "id": "SYNTH-INC-010",
        "title": "CoreDNS internal DNS resolution failure",
        "description": "Internal microservices unable to resolve service.cluster.local hostnames. Inter-service calls failing with NXDOMAIN.",
        "status": "Resolved",
        "severity": "P1",
        "priority": "P1",
        "category": "DevOps",
        "affected_systems": ["coredns", "kube-dns", "cluster-networking"],
        "assignment_team": "DevOps",
        "source": "synthetic_multimodal",
        "created_at": "2026-03-23T15:30:00Z",
        "updated_at": "2026-03-23T16:15:00Z",
        "resolved_at": "2026-03-23T16:15:00Z",
        "confidence": 0.96,
        "root_cause": "CoreDNS ConfigMap had corrupted autopath configuration following automated helm chart upgrade.",
        "recommended_solution": "Restore CoreDNS ConfigMap to verified backup; roll restart coredns deployment.",
        "executive_summary": "P1 cluster DNS outage resolved by restoring CoreDNS configuration and restarting pods.",
        "bug_report": {
            "title": "CoreDNS autopath plugin syntax error post-upgrade",
            "summary": "Invalid directive in Corefile prevented DNS resolution daemon from launching.",
            "environment": "Prod Kubernetes Cluster",
            "steps_to_reproduce": ["Apply helm upgrade with unescaped plugin parameter", "Inspect coredns pod logs"],
            "expected_behavior": "CoreDNS parses configuration without errors",
            "actual_behavior": "CoreDNS crashes on startup with Config error",
            "severity": "P1",
            "suspected_component": "k8s:coredns"
        },
        "timeline": [
            {"timestamp": "2026-03-23T15:30:00Z", "event": "Cluster-wide DNS failure alerts triggered", "is_approximate": False},
            {"timestamp": "2026-03-23T15:55:00Z", "event": "CoreDNS ConfigMap restored from GitOps repository", "is_approximate": False},
            {"timestamp": "2026-03-23T16:15:00Z", "event": "DNS resolution verified across all namespaces", "is_approximate": False}
        ],
        "metadata": {"is_synthetic": True}
    }
]

def generate_synthetic_incidents(output_file: str = None) -> List[Dict[str, Any]]:
    """Generates 10 realistic synthetic multimodal incident scenarios."""
    if output_file is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_file = os.path.join(base_dir, "data", "synthetic", "synthetic_incidents.json")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(SYNTHETIC_SCENARIOS, f, indent=2, ensure_ascii=False)

    logger.info(f"Generated {len(SYNTHETIC_SCENARIOS)} synthetic multimodal scenarios at: {output_file}")
    return SYNTHETIC_SCENARIOS

if __name__ == "__main__":
    generate_synthetic_incidents()
