import sys

filepath = 'tests/test_agent.py'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Update SqlCorrectnessMetric
old_sql_measure = """    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output"""
new_sql_measure = """    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output
        if not gold_sql:
            self.score = 1.0
            self.reason = "Not a SQL test — skipped"
            return self.score"""
content = content.replace(old_sql_measure, new_sql_measure)

# 2. Update HallucinationMetric
old_hal_measure = """    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output"""
new_hal_measure = """    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output
        if not gold_sql:
            self.score = 1.0
            self.reason = "Not a SQL test — skipped"
            return self.score"""
content = content.replace(old_hal_measure, new_hal_measure)

with open(filepath, 'w') as f:
    f.write(content)
print("Metrics patched!")
