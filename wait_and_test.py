#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""等待后端启动并测试"""
import time
import subprocess

print("等待后端启动...")
time.sleep(10)

print("\n执行测试...")
subprocess.run(["python", "test_call_tree_full.py"])
