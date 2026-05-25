from enum import Enum


class CaseType(str, Enum):
    UI = "UI"
    API = "API"
    PERFORMANCE = "PERFORMANCE"


class CaseStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class BodyType(str, Enum):
    NONE = "NONE"
    JSON = "JSON"
    FORM = "FORM"
    XML = "XML"
    RAW = "RAW"


class Priority(str, Enum):
    BVT = "BVT"
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResultStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"
    ERROR = "ERROR"


class NodeType(str, Enum):
    PLAYWRIGHT = "PLAYWRIGHT"
    LOCUST = "LOCUST"
    MIXED = "MIXED"


class OperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"


class ResourceType(str, Enum):
    USER = "USER"
    CASE = "CASE"
    TASK = "TASK"
    RESULT = "RESULT"
    NODE = "NODE"
    SYSTEM = "SYSTEM"
