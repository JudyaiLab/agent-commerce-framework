# Multi-Agent Swarm Template

A working 5-agent economy where agents discover, evaluate, buy, and sell services autonomously.

## Agents

| Agent | Role | What It Does |
|-------|------|-------------|
| Discovery Agent | Scout | Searches marketplace for services matching criteria |
| Quality Agent | Evaluator | Checks reputation scores, filters low-quality services |
| Buyer Agent | Purchaser | Executes purchases with balance management |
| Orchestrator | Coordinator | Routes tasks to the right agent, tracks budget |
| Reporter | Analyst | Logs all transactions, computes ROI |

## Quick Start

```bash
# 1. Configure
cp config.example.yaml config.yaml
# Edit with your marketplace credentials

# 2. Run the swarm
python swarm.py

# 3. Watch agents trade
# The swarm will discover services, evaluate quality,
# make purchases, and report results automatically.
```

## Architecture

```
Orchestrator
    |
    |-- Discovery Agent --> marketplace search
    |-- Quality Agent   --> reputation check
    |-- Buyer Agent     --> proxy call + payment
    |-- Reporter        --> transaction log + ROI
```

## Customization

- Edit `config.yaml` to set budget limits and search criteria
- Add new agent types in `agents/`
- Modify orchestrator logic in `swarm.py`
