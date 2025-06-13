#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Task Management System
A comprehensive Python example demonstrating various concepts for SonarQube analysis.

Author: Your Name
Date: 2023-07-12
"""

import logging
import uuid
import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json
import threading
import queue
import time
import os
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom Exceptions
class TaskManagementException(Exception):
    """Base exception for all task management related errors"""
    pass

class TaskNotFoundException(TaskManagementException):
    """Raised when a task is not found"""
    pass

class InvalidTaskStateException(TaskManagementException):
    """Raised when trying to transition to an invalid state"""
    pass

class UserNotAuthorizedException(TaskManagementException):
    """Raised when user doesn't have permission for an operation"""
    pass

# Enums
class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"

# Data Structures
@dataclass
class User:
    """User data structure"""
    id: str
    username: str
    email: str
    role: str
    
    def __post_init__(self):
        """Validate user data"""
        if not self.email or '@' not in self.email:
            raise ValueError("Invalid email address")

class Task:
    """Task class representing a task in the system"""
    
    def __init__(self, title: str, description: str, assigned_to: Optional[User] = None, 
                 priority: TaskPriority = TaskPriority.MEDIUM):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.status = TaskStatus.TODO
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at
        self.assigned_to = assigned_to
        self.priority = priority
        self.comments: List[str] = []
        self.tags: List[str] = []
        self._history: List[Dict[str, Any]] = []
        self._record_history("Task created")
        
    def _record_history(self, action: str) -> None:
        """Records an action in the task history"""
        self._history.append({
            "timestamp": datetime.datetime.now(),
            "action": action
        })
        self.updated_at = datetime.datetime.now()
    
    def assign(self, user: User) -> None:
        """Assign task to a user"""
        self.assigned_to = user
        self._record_history(f"Assigned to {user.username}")
    
    def change_status(self, new_status: TaskStatus) -> None:
        """Change task status"""
        # Validate status transition
        valid_transitions = {
            TaskStatus.TODO: [TaskStatus.IN_PROGRESS],
            TaskStatus.IN_PROGRESS: [TaskStatus.REVIEW, TaskStatus.TODO],
            TaskStatus.REVIEW: [TaskStatus.IN_PROGRESS, TaskStatus.DONE],
            TaskStatus.DONE: [TaskStatus.ARCHIVED],
            TaskStatus.ARCHIVED: []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise InvalidTaskStateException(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
            
        old_status = self.status
        self.status = new_status
        self._record_history(f"Status changed from {old_status.value} to {new_status.value}")
    
    def add_comment(self, comment: str) -> None:
        """Add a comment to the task"""
        if not comment.strip():
            return
        
        self.comments.append(comment)
        self._record_history(f"Comment added: {comment[:30]}...")
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task"""
        if tag.strip() and tag not in self.tags:
            self.tags.append(tag)
            self._record_history(f"Tag added: {tag}")
            
    def get_history(self) -> List[Dict[str, Any]]:
        """Get task history"""
        return self._history.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_to": self.assigned_to.username if self.assigned_to else None,
            "priority": self.priority.name,
            "comments": self.comments,
            "tags": self.tags
        }
        
    def __str__(self) -> str:
        """String representation of task"""
        return f"Task({self.id}): {self.title} - {self.status.value}"


# Abstract base class
class TaskStorage(ABC):
    """Abstract base class for task storage implementations"""
    
    @abstractmethod
    def save_task(self, task: Task) -> None:
        """Save a task"""
        pass
    
    @abstractmethod
    def get_task(self, task_id: str) -> Task:
        """Get a task by ID"""
        pass
    
    @abstractmethod
    def delete_task(self, task_id: str) -> None:
        """Delete a task by ID"""
        pass
    
    @abstractmethod
    def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Task]:
        """List tasks with optional filters"""
        pass


# Concrete implementation of TaskStorage
class InMemoryTaskStorage(TaskStorage):
    """In-memory implementation of TaskStorage"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        
    def save_task(self, task: Task) -> None:
        """Save a task to in-memory storage"""
        with self._lock:
            self.tasks[task.id] = task
            
    def get_task(self, task_id: str) -> Task:
        """Get a task by ID from in-memory storage"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                raise TaskNotFoundException(f"Task with ID {task_id} not found")
            return task
    
    def delete_task(self, task_id: str) -> None:
        """Delete a task by ID from in-memory storage"""
        with self._lock:
            if task_id not in self.tasks:
                raise TaskNotFoundException(f"Task with ID {task_id} not found")
            del self.tasks[task_id]
            
    def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Task]:
        """List tasks with optional filters from in-memory storage"""
        with self._lock:
            if not filters:
                return list(self.tasks.values())
            
            result = []
            for task in self.tasks.values():
                match = True
                for key, value in filters.items():
                    if key == "status" and isinstance(value, TaskStatus):
                        if task.status != value:
                            match = False
                            break
                    elif key == "assigned_to" and isinstance(value, User):
                        if task.assigned_to != value:
                            match = False
                            break
                    elif key == "tags" and isinstance(value, list):
                        if not all(tag in task.tags for tag in value):
                            match = False
                            break
                if match:
                    result.append(task)
            return result


class FileTaskStorage(TaskStorage):
    """File-based implementation of TaskStorage"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        
        # Load tasks from file if it exists
        try:
            self._load_tasks()
        except Exception as e:
            logger.error(f"Error loading tasks from file: {e}")
            
    def _load_tasks(self) -> None:
        """Load tasks from file"""
        if not os.path.exists(self.file_path):
            return
            
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                
            tasks_data = data.get('tasks', [])
            for task_data in tasks_data:
                task = Task(
                    title=task_data['title'],
                    description=task_data['description']
                )
                task.id = task_data['id']
                task.status = TaskStatus(task_data['status'])
                task.created_at = datetime.datetime.fromisoformat(task_data['created_at'])
                task.updated_at = datetime.datetime.fromisoformat(task_data['updated_at'])
                task.comments = task_data.get('comments', [])
                task.tags = task_data.get('tags', [])
                task.priority = TaskPriority[task_data.get('priority', 'MEDIUM')]
                
                self.tasks[task.id] = task
                
        except Exception as e:
            logger.error(f"Error parsing tasks file: {e}")
            raise
            
    def _save_to_file(self) -> None:
        """Save tasks to file"""
        try:
            tasks_data = []
            for task in self.tasks.values():
                tasks_data.append(task.to_dict())
                
            data = {
                'tasks': tasks_data,
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving tasks to file: {e}")
            raise
    
    def save_task(self, task: Task) -> None:
        """Save a task to file storage"""
        with self._lock:
            self.tasks[task.id] = task
            self._save_to_file()
            
    def get_task(self, task_id: str) -> Task:
        """Get a task by ID from file storage"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                raise TaskNotFoundException(f"Task with ID {task_id} not found")
            return task
    
    def delete_task(self, task_id: str) -> None:
        """Delete a task by ID from file storage"""
        with self._lock:
            if task_id not in self.tasks:
                raise TaskNotFoundException(f"Task with ID {task_id} not found")
            del self.tasks[task_id]
            self._save_to_file()
            
    def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Task]:
        """List tasks with optional filters from file storage"""
        with self._lock:
            if not filters:
                return list(self.tasks.values())
            
            result = []
            for task in self.tasks.values():
                match = True
                for key, value in filters.items():
                    if key == "status" and isinstance(value, TaskStatus):
                        if task.status != value:
                            match = False
                            break
                    elif key == "assigned_to" and isinstance(value, User):
                        if task.assigned_to != value:
                            match = False
                            break
                    elif key == "tags" and isinstance(value, list):
                        if not all(tag in task.tags for tag in value):
                            match = False
                            break
                if match:
                    result.append(task)
            return result


# Task Manager - Higher level class that uses TaskStorage
class TaskManager:
    """Task Manager class for managing tasks"""
    
    def __init__(self, storage: TaskStorage):
        self.storage = storage
        
    def create_task(self, title: str, description: str, assigned_to: Optional[User] = None, 
                    priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        """Create a new task"""
        # Input validation
        if not title.strip():
            raise ValueError("Task title cannot be empty")
            
        task = Task(title, description, assigned_to, priority)
        self.storage.save_task(task)
        
        logger.info(f"Created task: {task.id}")
        return task
    
    def get_task(self, task_id: str) -> Task:
        """Get a task by ID"""
        try:
            return self.storage.get_task(task_id)
        except TaskNotFoundException:
            logger.warning(f"Attempted to get non-existent task: {task_id}")
            raise
    
    def update_task(self, task_id: str, **kwargs) -> Task:
        """Update a task"""
        task = self.get_task(task_id)
        
        if 'title' in kwargs and kwargs['title'].strip():
            task.title = kwargs['title']
            
        if 'description' in kwargs:
            task.description = kwargs['description']
            
        if 'status' in kwargs and isinstance(kwargs['status'], TaskStatus):
            task.change_status(kwargs['status'])
            
        if 'assigned_to' in kwargs and isinstance(kwargs['assigned_to'], User):
            task.assign(kwargs['assigned_to'])
            
        if 'priority' in kwargs and isinstance(kwargs['priority'], TaskPriority):
            task.priority = kwargs['priority']
            
        if 'comment' in kwargs and kwargs['comment'].strip():
            task.add_comment(kwargs['comment'])
            
        if 'tag' in kwargs and kwargs['tag'].strip():
            task.add_tag(kwargs['tag'])
            
        self.storage.save_task(task)
        logger.info(f"Updated task: {task.id}")
        
        return task
    
    def delete_task(self, task_id: str) -> None:
        """Delete a task"""
        try:
            self.storage.delete_task(task_id)
            logger.info(f"Deleted task: {task_id}")
        except TaskNotFoundException:
            logger.warning(f"Attempted to delete non-existent task: {task_id}")
            raise
    
    def list_tasks(self, **filters) -> List[Task]:
        """List tasks with filters"""
        filter_dict = {}
        
        if 'status' in filters and isinstance(filters['status'], TaskStatus):
            filter_dict['status'] = filters['status']
            
        if 'assigned_to' in filters and isinstance(filters['assigned_to'], User):
            filter_dict['assigned_to'] = filters['assigned_to']
            
        if 'tags' in filters and isinstance(filters['tags'], list):
            filter_dict['tags'] = filters['tags']
            
        return self.storage.list_tasks(filter_dict)
    
    def get_tasks_by_priority(self) -> Dict[TaskPriority, List[Task]]:
        """Get tasks grouped by priority"""
        tasks = self.storage.list_tasks()
        grouped_tasks = {
            TaskPriority.LOW: [],
            TaskPriority.MEDIUM: [],
            TaskPriority.HIGH: [],
            TaskPriority.CRITICAL: []
        }
        
        for task in tasks:
            grouped_tasks[task.priority].append(task)
            
        return grouped_tasks
    
    def get_overdue_tasks(self, due_date_field: str = 'updated_at', 
                         days_threshold: int = 7) -> List[Task]:
        """Get tasks that haven't been updated for a certain number of days"""
        all_tasks = self.storage.list_tasks()
        overdue_tasks = []
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        
        for task in all_tasks:
            if getattr(task, due_date_field) < threshold_date:
                overdue_tasks.append(task)
                
        return overdue_tasks


# Background Task Processing with Threading
class TaskProcessor:
    """Process tasks in background"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.task_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        
    def start(self) -> None:
        """Start the task processor"""
        if self.running:
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("Task processor started")
        
    def stop(self) -> None:
        """Stop the task processor"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None
        logger.info("Task processor stopped")
        
    def _process_tasks(self) -> None:
        """Process tasks from queue"""
        while self.running:
            try:
                if self.task_queue.empty():
                    time.sleep(0.5)
                    continue
                    
                task_info = self.task_queue.get(block=False)
                action = task_info.get('action')
                
                if action == 'process_task':
                    self._handle_task_processing(task_info.get('task_id'))
                elif action == 'archive_old_tasks':
                    self._handle_task_archiving(task_info.get('days', 30))
                    
                self.task_queue.task_done()
                
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error in task processor: {e}")
                
    def _handle_task_processing(self, task_id: str) -> None:
        """Handle task processing"""
        try:
            task = self.task_manager.get_task(task_id)
            logger.info(f"Processing task {task_id}: {task.title}")
            
            # Simulate some task processing
            time.sleep(1)
            
            # Update the task with a processing comment
            self.task_manager.update_task(
                task_id, 
                comment=f"Processed automatically at {datetime.datetime.now().isoformat()}"
            )
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
    
    def _handle_task_archiving(self, days: int) -> None:
        """Handle archiving old tasks"""
        try:
            logger.info(f"Archiving tasks older than {days} days")
            
            # Get tasks that are done and haven't been updated in the specified days
            all_tasks = self.task_manager.list_tasks(status=TaskStatus.DONE)
            threshold_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            for task in all_tasks:
                if task.updated_at < threshold_date:
                    logger.info(f"Archiving task {task.id}: {task.title}")
                    try:
                        self.task_manager.update_task(task.id, status=TaskStatus.ARCHIVED)
                    except Exception as e:
                        logger.error(f"Error archiving task {task.id}: {e}")
            
        except Exception as e:
            logger.error(f"Error during task archiving: {e}")
    
    def enqueue_task_processing(self, task_id: str) -> None:
        """Enqueue a task for processing"""
        self.task_queue.put({
            'action': 'process_task',
            'task_id': task_id
        })
        
    def enqueue_task_archiving(self, days: int = 30) -> None:
        """Enqueue task archiving"""
        self.task_queue.put({
            'action': 'archive_old_tasks',
            'days': days
        })


# Data structure and algorithm example: Graph for task dependencies
class TaskNode:
    """Node in a task dependency graph"""
    
    def __init__(self, task: Task):
        self.task = task
        self.dependencies = []  # Tasks that this task depends on
        self.dependents = []    # Tasks that depend on this task
        
    def add_dependency(self, node: 'TaskNode') -> None:
        """Add a dependency to this task"""
        if node not in self.dependencies:
            self.dependencies.append(node)
            node.dependents.append(self)
            
    def remove_dependency(self, node: 'TaskNode') -> None:
        """Remove a dependency from this task"""
        if node in self.dependencies:
            self.dependencies.remove(node)
            node.dependents.remove(self)


class TaskDependencyGraph:
    """Graph for managing task dependencies"""
    
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}  # Map from task ID to node
        
    def add_task(self, task: Task) -> None:
        """Add a task to the graph"""
        if task.id not in self.nodes:
            self.nodes[task.id] = TaskNode(task)
            
    def add_dependency(self, dependent_task_id: str, dependency_task_id: str) -> None:
        """Add a dependency between tasks"""
        if dependent_task_id not in self.nodes or dependency_task_id not in self.nodes:
            raise TaskNotFoundException("Task not found in dependency graph")
            
        dependent_node = self.nodes[dependent_task_id]
        dependency_node = self.nodes[dependency_task_id]
        
        # Check for circular dependencies
        if self._would_create_cycle(dependent_node, dependency_node):
            raise ValueError("Adding this dependency would create a cycle")
            
        dependent_node.add_dependency(dependency_node)
        
    def _would_create_cycle(self, start_node: TaskNode, end_node: TaskNode) -> bool:
        """Check if adding a dependency would create a cycle"""
        # If end_node depends on start_node already, adding a reverse dependency would create a cycle
        visited = set()
        queue = [end_node]
        
        while queue:
            current = queue.pop(0)
            if current == start_node:
                return True
                
            if current in visited:
                continue
                
            visited.add(current)
            queue.extend([node for node in current.dependencies if node not in visited])
            
        return False
    
    def get_dependent_tasks(self, task_id: str) -> List[Task]:
        """Get tasks that directly depend on this task"""
        if task_id not in self.nodes:
            raise TaskNotFoundException(f"Task {task_id} not found")
            
        return [node.task for node in self.nodes[task_id].dependents]
    
    def get_dependency_tasks(self, task_id: str) -> List[Task]:
        """Get tasks that this task directly depends on"""
        if task_id not in self.nodes:
            raise TaskNotFoundException(f"Task {task_id} not found")
            
        return [node.task for node in self.nodes[task_id].dependencies]
    
    def get_all_dependencies(self, task_id: str) -> List[Task]:
        """Get all tasks that this task depends on (directly or indirectly)"""
        if task_id not in self.nodes:
            raise TaskNotFoundException(f"Task {task_id} not found")
            
        dependencies = []
        visited = set()
        
        def collect_dependencies(node):
            for dep_node in node.dependencies:
                if dep_node.task.id not in visited:
                    visited.add(dep_node.task.id)
                    dependencies.append(dep_node.task)
                    collect_dependencies(dep_node)
                    
        start_node = self.nodes[task_id]
        collect_dependencies(start_node)
        
        return dependencies
    
    def topological_sort(self) -> List[Task]:
        """Sort tasks in topological order (dependency-first)"""
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node_id):
            if node_id in temp_visited:
                raise ValueError("Graph has a cycle")
                
            if node_id in visited:
                return
                
            temp_visited.add(node_id)
            node = self.nodes[node_id]
            
            for dep_node in node.dependencies:
                visit(dep_node.task.id)
                
            temp_visited.remove(node_id)
            visited.add(node_id)
            result.append(node.task)
            
        for node_id in self.nodes:
            if node_id not in visited:
                visit(node_id)
                
        return list(reversed(result))  # Reverse to get dependency-first order


# Main demonstration function 
def main():
    try:
        # Create users
        alice = User(id="1", username="alice", email="alice@example.com", role="admin")
        bob = User(id="2", username="bob", email="bob@example.com", role="developer")
        
        # Create task storage and manager
        task_storage = InMemoryTaskStorage()
        task_manager = TaskManager(task_storage)
        
        # Create some tasks
        task1 = task_manager.create_task(
            "Implement authentication", 
            "Add JWT authentication to the API", 
            alice, 
            TaskPriority.HIGH
        )
        
        task2 = task_manager.create_task(
            "Write unit tests", 
            "Create comprehensive test suite for the auth module", 
            bob, 
            TaskPriority.MEDIUM
        )
        
        task3 = task_manager.create_task(
            "Deploy to staging", 
            "Deploy latest changes to the staging environment", 
            None, 
            TaskPriority.LOW
        )
        
        # Update tasks
        task_manager.update_task(task1.id, status=TaskStatus.IN_PROGRESS)
        task_manager.update_task(task1.id, comment="Started working on JWT implementation")
        
        task_manager.update_task(task2.id, tag="testing")
        task_manager.update_task(task2.id, tag="auth")
        
        # Create task dependency graph
        dependency_graph = TaskDependencyGraph()
        dependency_graph.add_task(task1)
        dependency_graph.add_task(task2)
        dependency_graph.add_task(task3)
        
        # Add dependencies
        dependency_graph.add_dependency(task2.id, task1.id)  # Tests depend on implementation
        dependency_graph.add_dependency(task3.id, task2.id)  # Deploy depends on tests
        
        # Get tasks in topological order
        ordered_tasks = dependency_graph.topological_sort()
        print("Tasks in dependency order:")
        for task in ordered_tasks:
            print(f"  {task.title}")
        
        # Start background processing
        processor = TaskProcessor(task_manager)
        processor.start()
        
        # Enqueue some tasks for background processing
        processor.enqueue_task_processing(task1.id)
        processor.enqueue_task_archiving(days=14)
        
        # Wait for background processing to complete
        time.sleep(3)
        
        # Stop background processing
        processor.stop()
        
        print("\nTask summary:")
        for task in task_manager.list_tasks():
            print(f"- {task.title} ({task.status.value}) - Assigned to: {task.assigned_to.username if task.assigned_to else 'Unassigned'}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
        
        
if __name__ == "__main__":
    main()
