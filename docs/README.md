# Jira Work Items Manager

A Python-based CLI tool for connecting to your Jira board, viewing work items, analyzing them, and adding comments.

## Features

- 🔗 Connect to Jira using API tokens
- 📋 List and view work items (issues)
- 🔍 Analyze issues with insights and statistics
- 💬 Add comments to issues
- 📊 Generate comprehensive analysis reports
- 🎨 Beautiful CLI interface with rich formatting

## Prerequisites

- Python 3.7 or higher
- Jira account with API access
- Jira API token

## Installation

1. Clone or navigate to this directory:
```bash
cd /Users/eslamfawzy/Desktop/Mobility/Prompts/AI-Demo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Get your Jira API token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token

2. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

3. Edit `.env` with your credentials:
```
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=PROJ  # Optional: default project key
```

## Usage

### Quick commands (QA)

From the project root you can run:

| Command | Description |
|--------|-------------|
| `./analyze <key>` | Run full story analysis and save to `analysis/analysis-<key>.md`. |
| `./generate-tc <key>` | Generate test cases and save to `test-suite/test-cases-<key>.md`. |

**Examples:**
```bash
./analyze CMB-32860
./generate-tc CMB-32860
```

To use without `./`, add the project to your `PATH` or create aliases:
```bash
export PATH="/path/to/AI-Demo:$PATH"
analyze CMB-32860
generate-tc CMB-32860
```

Same commands via Python:
```bash
python3 main.py analyze CMB-32860
python3 main.py generate-tc CMB-32860
```

### Interactive Mode (Recommended)

Run without arguments to enter interactive mode:
```bash
python main.py
```

### Command Line Mode

#### List Issues
```bash
# List all issues
python main.py list

# List issues from a specific project
python main.py list --project PROJ

# List issues with custom JQL query
python main.py list --jql "status = 'In Progress'"

# List and analyze
python main.py list --project PROJ --analyze
```

#### View Issue Details
```bash
# View a specific issue
python main.py view PROJ-123

# View with comments
python main.py view PROJ-123 --comments

# View with analysis
python main.py view PROJ-123 --analyze
```

#### Add Comment
```bash
# Add comment (will prompt for text)
python main.py comment PROJ-123

# Add comment with text
python main.py comment PROJ-123 --text "This looks good!"
```

#### Analyze Issues
```bash
# Analyze all issues in a project
python main.py analyze --project PROJ

# Analyze a specific issue
python main.py analyze PROJ-123

# Analyze with custom JQL
python main.py analyze --jql "assignee = currentUser()"
```

## Examples

### Example 1: View all issues in a project
```bash
python main.py list --project PROJ --limit 20
```

### Example 2: Analyze and comment on an issue
```bash
# First, view and analyze
python main.py view PROJ-123 --analyze

# Then add a comment
python main.py comment PROJ-123 --text "Reviewed and approved"
```

### Example 3: Get statistics on all open issues
```bash
python main.py analyze --jql "status != Done" --limit 100
```

## JQL Query Examples

You can use JQL (Jira Query Language) to filter issues:

- `project = PROJ` - All issues in project PROJ
- `status = "In Progress"` - All in-progress issues
- `assignee = currentUser()` - Issues assigned to you
- `priority = High` - High priority issues
- `created >= -7d` - Issues created in the last 7 days
- `status != Done AND assignee = currentUser()` - Your incomplete issues

## Troubleshooting

### Connection Issues
- Verify your `.env` file has correct credentials
- Check that your Jira server URL is correct (include `https://`)
- Ensure your API token is valid and not expired

### Permission Issues
- Make sure your Jira account has permission to view the projects/issues
- API tokens inherit your user permissions

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Use a virtual environment to avoid conflicts

## License

This project is provided as-is for personal use.
