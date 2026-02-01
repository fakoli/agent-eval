# Skill Testing Template

Use this template to test your own skill.

## Setup

1. Copy this folder:
   ```bash
   cp -r _template/ my-skill-test/
   ```

2. Add your skill to `skills/`:
   ```bash
   mkdir -p my-skill-test/skills/my-skill
   cp /path/to/your/skill/* my-skill-test/skills/my-skill/
   ```

3. Update `configs/with-skill/config.yaml`:
   ```yaml
   name: with-my-skill
   description: Testing my skill
   skills_path: ../skills/my-skill
   # ... rest of config
   ```

4. Create your fixture in `fixtures/`:
   - This should be a codebase with intentional issues your skill helps fix
   - Include tests that verify the fix

5. Create task files in `tasks/`:
   - Copy and modify `tasks/your-task.task.yaml.example`
   - Each task should test a specific principle from your skill

6. Run the comparison:
   ```bash
   # Make sure ANTHROPIC_API_KEY is set
   export ANTHROPIC_API_KEY="your-key"

   uv run python -m harness matrix \
     --tasks "examples/skill-testing/my-skill-test/tasks/*.yaml" \
     --configs "examples/skill-testing/my-skill-test/configs/*/config.yaml" \
     --runs 3
   ```

## Tips

- **Focus on measurable outcomes**: Don't test "write good code", test "always validate input at boundaries"
- **Match tasks to principles**: If your skill says "use dependency injection", create a task that benefits from DI
- **Include failing tests**: Your fixture should have tests that fail until the AI fixes the code
