SYSTEM_TEMPLATE = """\
You are a puzzle evaluator in a 2D physics environment.
Puzzle ID: <PUZZLE_ID>
Description: <DESCRIPTION>

We want to see if a certain proposal leads to the goal being met.
Here is the puzzle's image(s): <IMAGES>

Few-Shot Examples:
<FEW_SHOT>
"""

USER_TEMPLATE = """\
Please analyze the puzzle and proposal:
 - Proposal Tier: {{PROPOSAL_TIER}}
 - The ball is placed at X={{PROP_POS_X}}, Y={{PROP_POS_Y}}, radius={{PROP_RADIUS}}

Question:
  Will the two target bodies collide for the required 3 seconds?
  
Answer only with 'YES' or 'NO'.
"""
