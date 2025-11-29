# Scenario Reference (context for result evaluation)

Use this as ground truth context for interpreting pipeline outputs. It captures what actually happened in each scenario, not the model’s results.

## real_173442
- Indoor office/residential-like environment.
- Robot should be comfortably within ODD.
- No intentional collisions; no hazards beyond normal clutter.
- Terrain expected to be smooth/slightly rough only; no stairs in path.

## real_173813
- Indoor scene; robot completely stationary for entire run.
- No intentional motion; environment otherwise benign.
- No intentional collisions; any collision detection should be scrutinized.

## real_174232
- Intentional collision scenario: robot driven into a cardboard box.
- Environment otherwise typical indoor; terrain expected smooth/slightly rough.
- Collisions expected at the contact point with the box.

## real_174321
- Ramp traversal with aggressive driving; also contacted a cabinet.
- Expect elevated pitch/roll beyond normal ODD limits on ramp.
- Multiple collisions plausible (ramp taps + cabinet impact).
- Terrain: ramp present; roughness should reflect elevation change, not texture.

## real_174503
- Smooth ramp traversal (controlled).
- Elevated pitch noted but stayed within ODD limits.
- No intentional collisions; terrain reflects ramp but should remain within limits.

## real_174604
- Indoor, robot stationary.
- Humans/animals present; a person approaches closely near the end (should be OOD on proximity).
- No intended collisions; any collision reports should require strong evidence given zero motion.
- Terrain expected smooth/slightly rough; obstacle density modest.

## sim_1
- Simulation; robot deliberately driven through objects in the scene.
- Intentional collisions present.
- A max roll violation occurred; should be noted with reasoning.
- Other conditions follow sim indoor environment; density should match actual BEV occupancy.
