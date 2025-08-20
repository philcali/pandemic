# Event Bus Usage Examples

## Real-World Use Cases

### 1. Monitoring Dashboard (pandemic-console)

```python
# pandemic-console subscribes to all system events for real-time dashboard
from pandemic_common import EventManager

class DashboardEventHandler:
    def __init__(self):
        self.manager = EventManager("pandemic-console")
        self.connected_clients = []  # WebSocket connections
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to all core system events
        await self.manager.add_subscription("core", "**", self.handle_system_event)
        
        # Subscribe to metrics from all infections
        infections = await self.get_all_infections()
        for infection_id in infections:
            await self.manager.add_subscription(infection_id, "metric.**", self.handle_metric_event)
    
    async def handle_system_event(self, event):
        # Forward system events to dashboard clients
        message = {
            "type": "system_event",
            "event": event.type,
            "source": event.source,
            "payload": event.payload,
            "timestamp": event.timestamp
        }
        await self.broadcast_to_clients(message)
    
    async def handle_metric_event(self, event):
        # Update real-time metrics display
        if event.type.startswith("metric."):
            await self.update_metrics_display(event.source, event.payload)
```

### 2. Log Aggregation Service

```python
# Custom infection that aggregates logs from all other infections
from pandemic_common import EventManager
import json
import asyncio

class LogAggregator:
    def __init__(self):
        self.manager = EventManager("log-aggregator")
        self.log_buffer = []
        self.batch_size = 100
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to log events from all infections
        await self.manager.add_subscription("core", "**", self.handle_core_logs)
        
        # Subscribe to custom log events from infections
        infections = await self.discover_infections()
        for infection_id in infections:
            await self.manager.add_subscription(infection_id, "log.**", self.handle_infection_logs)
        
        # Start batch processing
        asyncio.create_task(self.process_log_batches())
    
    async def handle_core_logs(self, event):
        log_entry = {
            "timestamp": event.timestamp,
            "source": "core",
            "level": "INFO",
            "event_type": event.type,
            "message": f"Core event: {event.type}",
            "payload": event.payload
        }
        self.log_buffer.append(log_entry)
    
    async def handle_infection_logs(self, event):
        log_entry = {
            "timestamp": event.timestamp,
            "source": event.source,
            "level": event.payload.get("level", "INFO"),
            "event_type": event.type,
            "message": event.payload.get("message", ""),
            "payload": event.payload
        }
        self.log_buffer.append(log_entry)
    
    async def process_log_batches(self):
        while True:
            if len(self.log_buffer) >= self.batch_size:
                batch = self.log_buffer[:self.batch_size]
                self.log_buffer = self.log_buffer[self.batch_size:]
                
                # Send to external log system
                await self.send_to_elasticsearch(batch)
            
            await asyncio.sleep(5)  # Process every 5 seconds
```

### 3. Auto-Scaling Controller

```python
# Infection that monitors system load and scales other infections
from pandemic_common import EventManager, EventClient

class AutoScaler:
    def __init__(self):
        self.manager = EventManager("auto-scaler")
        self.load_metrics = {}
        self.scaling_rules = {
            "web-server": {"min": 2, "max": 10, "cpu_threshold": 80},
            "worker": {"min": 1, "max": 5, "queue_threshold": 100}
        }
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to metric events from all infections
        await self.manager.add_subscription("core", "infection.**", self.handle_infection_events)
        
        # Subscribe to custom metrics
        for infection_type in self.scaling_rules.keys():
            pattern = f"metric.{infection_type}.**"
            await self.manager.add_subscription("*", pattern, self.handle_metrics)
        
        # Start scaling loop
        asyncio.create_task(self.scaling_loop())
    
    async def handle_infection_events(self, event):
        if event.type == "infection.started":
            infection_id = event.payload["infectionId"]
            await self.manager.add_subscription(infection_id, "metric.**", self.handle_metrics)
    
    async def handle_metrics(self, event):
        source = event.source
        if event.type == "metric.cpu":
            self.load_metrics[source] = event.payload
            await self.check_scaling_needed(source)
    
    async def check_scaling_needed(self, infection_id):
        metrics = self.load_metrics.get(infection_id, {})
        cpu_usage = metrics.get("cpu_percent", 0)
        
        # Determine infection type from ID or config
        infection_type = await self.get_infection_type(infection_id)
        rules = self.scaling_rules.get(infection_type)
        
        if rules and cpu_usage > rules["cpu_threshold"]:
            await self.scale_up(infection_type)
        elif rules and cpu_usage < rules["cpu_threshold"] * 0.5:
            await self.scale_down(infection_type)
    
    async def scale_up(self, infection_type):
        # Publish scaling event
        await self.manager.publish("scaling.up", {
            "infection_type": infection_type,
            "reason": "high_cpu_usage"
        })
        
        # Trigger new infection installation
        await self.install_new_infection(infection_type)
```

### 4. Security Monitor

```python
# Security infection that monitors for suspicious events
from pandemic_common import EventManager
import re

class SecurityMonitor:
    def __init__(self):
        self.manager = EventManager("security-monitor")
        self.alert_patterns = [
            r".*failed.*login.*",
            r".*unauthorized.*access.*",
            r".*suspicious.*activity.*"
        ]
        self.alert_threshold = 5  # alerts per minute
        self.recent_alerts = []
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to all events for security monitoring
        await self.manager.add_subscription("core", "**", self.analyze_event)
        
        # Subscribe to all infection events
        infections = await self.get_all_infections()
        for infection_id in infections:
            await self.manager.add_subscription(infection_id, "**", self.analyze_event)
    
    async def analyze_event(self, event):
        # Check for security-related events
        event_text = f"{event.type} {json.dumps(event.payload)}"
        
        for pattern in self.alert_patterns:
            if re.search(pattern, event_text, re.IGNORECASE):
                await self.handle_security_alert(event, pattern)
                break
        
        # Monitor for infection failures (potential attacks)
        if event.type == "infection.failed":
            await self.investigate_failure(event)
    
    async def handle_security_alert(self, event, pattern):
        alert = {
            "timestamp": event.timestamp,
            "source": event.source,
            "event_type": event.type,
            "pattern_matched": pattern,
            "severity": "HIGH",
            "payload": event.payload
        }
        
        self.recent_alerts.append(alert)
        
        # Publish security alert
        await self.manager.publish("security.alert", alert)
        
        # Check for alert storm
        if len(self.recent_alerts) > self.alert_threshold:
            await self.handle_alert_storm()
    
    async def investigate_failure(self, event):
        infection_id = event.payload.get("infectionId")
        error = event.payload.get("error", "")
        
        # Check for signs of attack
        suspicious_errors = ["permission denied", "access forbidden", "authentication failed"]
        
        if any(sus in error.lower() for sus in suspicious_errors):
            await self.manager.publish("security.suspicious_failure", {
                "infectionId": infection_id,
                "error": error,
                "investigation_needed": True
            })
```

### 5. Performance Profiler

```python
# Infection that profiles system performance and publishes insights
from pandemic_common import EventManager
import psutil
import asyncio

class PerformanceProfiler:
    def __init__(self):
        self.manager = EventManager("performance-profiler")
        self.metrics_history = {}
        self.analysis_interval = 60  # seconds
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to all metric events
        await self.manager.add_subscription("core", "**", self.collect_core_metrics)
        
        infections = await self.get_all_infections()
        for infection_id in infections:
            await self.manager.add_subscription(infection_id, "metric.**", self.collect_infection_metrics)
        
        # Start profiling tasks
        asyncio.create_task(self.system_metrics_loop())
        asyncio.create_task(self.analysis_loop())
    
    async def collect_core_metrics(self, event):
        if event.type.startswith("infection."):
            # Track infection lifecycle timing
            await self.track_lifecycle_performance(event)
    
    async def collect_infection_metrics(self, event):
        source = event.source
        timestamp = event.timestamp
        
        if source not in self.metrics_history:
            self.metrics_history[source] = []
        
        self.metrics_history[source].append({
            "timestamp": timestamp,
            "type": event.type,
            "payload": event.payload
        })
        
        # Keep only recent history (last hour)
        cutoff = time.time() - 3600
        self.metrics_history[source] = [
            m for m in self.metrics_history[source] 
            if m["timestamp"] > cutoff
        ]
    
    async def system_metrics_loop(self):
        while True:
            # Collect system-wide metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            await self.manager.publish("metric.system", {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free
            })
            
            await asyncio.sleep(30)
    
    async def analysis_loop(self):
        while True:
            await asyncio.sleep(self.analysis_interval)
            
            # Analyze performance trends
            for infection_id, history in self.metrics_history.items():
                analysis = await self.analyze_infection_performance(infection_id, history)
                
                if analysis["recommendations"]:
                    await self.manager.publish("analysis.performance", {
                        "infectionId": infection_id,
                        "analysis": analysis,
                        "timestamp": time.time()
                    })
    
    async def analyze_infection_performance(self, infection_id, history):
        # Analyze CPU trends
        cpu_metrics = [h["payload"].get("cpu_percent", 0) for h in history if "cpu" in h["type"]]
        
        analysis = {
            "infectionId": infection_id,
            "recommendations": [],
            "trends": {}
        }
        
        if cpu_metrics:
            avg_cpu = sum(cpu_metrics) / len(cpu_metrics)
            max_cpu = max(cpu_metrics)
            
            analysis["trends"]["cpu"] = {
                "average": avg_cpu,
                "maximum": max_cpu,
                "samples": len(cpu_metrics)
            }
            
            if avg_cpu > 80:
                analysis["recommendations"].append({
                    "type": "high_cpu_usage",
                    "message": f"Average CPU usage is {avg_cpu:.1f}%, consider optimization",
                    "priority": "HIGH"
                })
            
            if max_cpu > 95:
                analysis["recommendations"].append({
                    "type": "cpu_spikes",
                    "message": f"CPU spikes detected (max: {max_cpu:.1f}%), investigate workload",
                    "priority": "MEDIUM"
                })
        
        return analysis
```

## Integration Patterns

### Event-Driven Workflows

```python
# Workflow orchestration using events
class WorkflowOrchestrator:
    def __init__(self):
        self.manager = EventManager("workflow-orchestrator")
        self.active_workflows = {}
    
    async def start(self):
        await self.manager.initialize()
        
        # Subscribe to workflow events
        await self.manager.add_subscription("*", "workflow.**", self.handle_workflow_event)
        await self.manager.add_subscription("*", "task.**", self.handle_task_event)
    
    async def handle_workflow_event(self, event):
        if event.type == "workflow.start":
            workflow_id = event.payload["workflow_id"]
            await self.start_workflow(workflow_id, event.payload)
        elif event.type == "workflow.step_complete":
            await self.advance_workflow(event.payload)
    
    async def start_workflow(self, workflow_id, config):
        # Initialize workflow state
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "steps": config["steps"],
            "current_step": 0,
            "status": "running"
        }
        
        # Start first step
        await self.execute_next_step(workflow_id)
    
    async def execute_next_step(self, workflow_id):
        workflow = self.active_workflows[workflow_id]
        current_step = workflow["current_step"]
        
        if current_step < len(workflow["steps"]):
            step = workflow["steps"][current_step]
            
            # Publish step execution event
            await self.manager.publish("workflow.execute_step", {
                "workflow_id": workflow_id,
                "step_id": step["id"],
                "step_config": step
            })
        else:
            # Workflow complete
            await self.complete_workflow(workflow_id)
```

### Circuit Breaker Pattern

```python
# Circuit breaker using events for failure detection
class CircuitBreaker:
    def __init__(self, infection_id):
        self.manager = EventManager(f"circuit-breaker-{infection_id}")
        self.target_infection = infection_id
        self.failure_count = 0
        self.failure_threshold = 5
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def start(self):
        await self.manager.initialize()
        
        # Monitor target infection for failures
        await self.manager.add_subscription(self.target_infection, "error.**", self.handle_error)
        await self.manager.add_subscription(self.target_infection, "success.**", self.handle_success)
    
    async def handle_error(self, event):
        self.failure_count += 1
        
        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            self.state = "OPEN"
            await self.manager.publish("circuit.opened", {
                "target": self.target_infection,
                "failure_count": self.failure_count
            })
    
    async def handle_success(self, event):
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            await self.manager.publish("circuit.closed", {
                "target": self.target_infection
            })
```

These examples demonstrate the power and flexibility of the event bus system for building reactive, event-driven applications within the Pandemic ecosystem.