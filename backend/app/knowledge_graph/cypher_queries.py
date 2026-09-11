"""
CodeSentinel Knowledge Graph Module: Cypher Query Catalog.

Centralized Cypher statements for graph materialization, idempotent upserts (MERGE),
subgraph purging, and the 4 named traversals.
"""

# Stale-Data Policy (MVP): On project reload, delete all nodes and relationships
# belonging to the project_id to rebuild fresh, avoiding stale dangling references.
DELETE_PROJECT_SUBGRAPH = """
MATCH (n {project_id: $project_id})
DETACH DELETE n
"""

# -------------------------------------------------------------------------
# Idempotent Node Upsert Queries (MERGE on unique keys)
# -------------------------------------------------------------------------

UPSERT_PROJECT_NODE = """
MERGE (p:Project {id: $id})
SET p.name = $name,
    p.repository_url = $repository_url,
    p.default_branch = $default_branch,
    p.project_id = $id,
    p.updated_at = datetime()
RETURN p
"""

UPSERT_FILE_NODE = """
MERGE (f:File {id: $id, project_id: $project_id})
SET f.path = $path,
    f.language = $language,
    f.name = $name,
    f.project_id = $project_id
RETURN f
"""

UPSERT_MODULE_NODE = """
MERGE (m:Module {id: $id, project_id: $project_id})
SET m.name = $name,
    m.qualified_name = $qualified_name,
    m.file_path = $file_path,
    m.project_id = $project_id
RETURN m
"""

UPSERT_CLASS_NODE = """
MERGE (c:Class {id: $id, project_id: $project_id})
SET c.name = $name,
    c.qualified_name = $qualified_name,
    c.file_path = $file_path,
    c.project_id = $project_id
RETURN c
"""

UPSERT_FUNCTION_NODE = """
MERGE (fn:Function {id: $id, project_id: $project_id})
SET fn.name = $name,
    fn.qualified_name = $qualified_name,
    fn.file_path = $file_path,
    fn.return_type = $return_type,
    fn.complexity_score = $complexity_score,
    fn.project_id = $project_id
RETURN fn
"""

UPSERT_API_NODE = """
MERGE (a:API {id: $id, project_id: $project_id})
SET a.path = $path,
    a.http_method = $http_method,
    a.summary = $summary,
    a.project_id = $project_id
RETURN a
"""

UPSERT_REQUIREMENT_NODE = """
MERGE (r:Requirement {id: $id, project_id: $project_id})
SET r.identifier = $identifier,
    r.title = $title,
    r.description = $description,
    r.req_type = $req_type,
    r.priority = $priority,
    r.status = $status,
    r.project_id = $project_id
RETURN r
"""

UPSERT_TEST_NODE = """
MERGE (t:Test {id: $id, project_id: $project_id})
SET t.name = $name,
    t.provenance = $provenance,
    t.test_type = $test_type,
    t.file_path = $file_path,
    t.project_id = $project_id
RETURN t
"""

UPSERT_EXECUTION_NODE = """
MERGE (e:Execution {id: $id, project_id: $project_id})
SET e.status = $status,
    e.environment = $environment,
    e.total_tests = $total_tests,
    e.passed_tests = $passed_tests,
    e.failed_tests = $failed_tests,
    e.project_id = $project_id
RETURN e
"""

UPSERT_FAILURE_NODE = """
MERGE (f:Failure {id: $id, project_id: $project_id})
SET f.title = $title,
    f.error_message = $error_message,
    f.category = $category,
    f.severity = $severity,
    f.project_id = $project_id
RETURN f
"""

UPSERT_FINDING_NODE = """
MERGE (find:Finding {id: $id, project_id: $project_id})
SET find.rule_id = $rule_id,
    find.title = $title,
    find.category = $category,
    find.severity = $severity,
    find.project_id = $project_id
RETURN find
"""

UPSERT_COMMIT_NODE = """
MERGE (cm:Commit {id: $id, project_id: $project_id})
SET cm.commit_hash = $commit_hash,
    cm.message = $message,
    cm.author = $author,
    cm.project_id = $project_id
RETURN cm
"""

# -------------------------------------------------------------------------
# Idempotent Relationship Queries
# -------------------------------------------------------------------------

REL_PROJECT_CONTAINS_FILE = """
MATCH (p:Project {id: $project_id}), (f:File {id: $file_id, project_id: $project_id})
MERGE (p)-[r:CONTAINS]->(f)
RETURN r
"""

REL_FILE_CONTAINS_FUNCTION = """
MATCH (f:File {id: $file_id, project_id: $project_id}), (fn:Function {id: $function_id, project_id: $project_id})
MERGE (f)-[r:CONTAINS]->(fn)
RETURN r
"""

REL_FILE_CONTAINS_CLASS = """
MATCH (f:File {id: $file_id, project_id: $project_id}), (c:Class {id: $class_id, project_id: $project_id})
MERGE (f)-[r:CONTAINS]->(c)
RETURN r
"""

REL_FUNCTION_CALLS_FUNCTION = """
MATCH (caller:Function {id: $caller_id, project_id: $project_id}), (callee:Function {id: $callee_id, project_id: $project_id})
MERGE (caller)-[r:CALLS]->(callee)
RETURN r
"""

REL_REQUIREMENT_IMPLEMENTED_BY_FUNCTION = """
MATCH (req:Requirement {id: $requirement_id, project_id: $project_id}), (fn:Function {id: $function_id, project_id: $project_id})
MERGE (req)-[r:IMPLEMENTED_BY]->(fn)
RETURN r
"""

REL_REQUIREMENT_TESTED_BY_TEST = """
MATCH (req:Requirement {id: $requirement_id, project_id: $project_id}), (t:Test {id: $test_id, project_id: $project_id})
MERGE (req)-[r:TESTED_BY]->(t)
RETURN r
"""

REL_TEST_EXECUTED_AS_EXECUTION = """
MATCH (t:Test {id: $test_id, project_id: $project_id}), (e:Execution {id: $execution_id, project_id: $project_id})
MERGE (t)-[r:EXECUTED_AS]->(e)
RETURN r
"""

REL_EXECUTION_PRODUCED_FAILURE = """
MATCH (e:Execution {id: $execution_id, project_id: $project_id}), (f:Failure {id: $failure_id, project_id: $project_id})
MERGE (e)-[r:PRODUCED]->(f)
RETURN r
"""

REL_FAILURE_RELATED_TO_FUNCTION = """
MATCH (f:Failure {id: $failure_id, project_id: $project_id}), (fn:Function {id: $function_id, project_id: $project_id})
MERGE (f)-[r:RELATED_TO]->(fn)
RETURN r
"""

REL_COMMIT_MODIFIES_FILE = """
MATCH (c:Commit {id: $commit_id, project_id: $project_id}), (f:File {id: $file_id, project_id: $project_id})
MERGE (c)-[r:MODIFIES]->(f)
RETURN r
"""

# -------------------------------------------------------------------------
# The 4 Named Traversal Queries
# -------------------------------------------------------------------------

# 1. "requirements with no linked test"
QUERY_UNTESTED_REQUIREMENTS = """
MATCH (r:Requirement {project_id: $project_id})
WHERE NOT (r)-[:TESTED_BY]->(:Test)
OPTIONAL MATCH (r)-[:IMPLEMENTED_BY]->(fn:Function)
RETURN r.id AS requirement_id,
       r.identifier AS identifier,
       r.title AS title,
       r.description AS description,
       r.priority AS priority,
       r.status AS status,
       collect(DISTINCT coalesce(fn.qualified_name, fn.name)) AS linked_functions
"""

# 2. "functions related to a given failure"
QUERY_FAILURE_RELATED_FUNCTIONS = """
MATCH (f:Failure {project_id: $project_id})
WHERE ($failure_id IS NULL OR f.id = $failure_id)
OPTIONAL MATCH (e:Execution)-[:PRODUCED]->(f)
OPTIONAL MATCH (f)-[:RELATED_TO]->(fn:Function)
RETURN f.id AS failure_id,
       f.title AS failure_title,
       f.error_message AS error_message,
       e.id AS execution_id,
       collect(DISTINCT {
           id: fn.id,
           name: fn.name,
           qualified_name: fn.qualified_name,
           file_path: fn.file_path
       }) AS related_functions
"""

# 3. "files changed by a commit and their dependent tests"
QUERY_COMMIT_IMPACT_AND_TESTS = """
MATCH (c:Commit {project_id: $project_id})
WHERE ($commit_hash IS NULL OR c.commit_hash = $commit_hash OR c.id = $commit_hash)
OPTIONAL MATCH (c)-[:MODIFIES]->(file:File)
OPTIONAL MATCH (file)-[:CONTAINS]->(fn:Function)
OPTIONAL MATCH (req:Requirement)-[:IMPLEMENTED_BY]->(fn)
OPTIONAL MATCH (req)-[:TESTED_BY]->(t:Test)
RETURN c.commit_hash AS commit_hash,
       collect(DISTINCT file.path) AS modified_files,
       collect(DISTINCT coalesce(fn.qualified_name, fn.name)) AS impacted_functions,
       collect(DISTINCT coalesce(t.name, t.file_path)) AS dependent_tests
"""

# 4. "call graph neighborhood of a function"
QUERY_CALL_NEIGHBORHOOD = """
MATCH (target:Function {project_id: $project_id})
WHERE target.name = $function_name OR target.qualified_name = $function_name OR target.id = $function_name
OPTIONAL MATCH (caller:Function)-[:CALLS]->(target)
OPTIONAL MATCH (target)-[:CALLS]->(callee:Function)
RETURN target.name AS target_function,
       collect(DISTINCT coalesce(caller.qualified_name, caller.name)) AS callers,
       collect(DISTINCT coalesce(callee.qualified_name, callee.name)) AS callees
"""

# Fetch complete project graph topology
QUERY_PROJECT_TOPOLOGY = """
MATCH (n {project_id: $project_id})
OPTIONAL MATCH (n)-[r]->(m {project_id: $project_id})
RETURN n, r, m
"""
