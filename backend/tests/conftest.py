"""Pytest configuration and global environment fixtures."""

import os

# Ensure LiteLLM uses local cached model cost map and never hits the network during test runs
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
