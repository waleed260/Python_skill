"""
Self-Documenting TIL (Today I Learned) Skill (Python)
Monitors Git history and generates learning notes for complex changes
"""

import os
import re
import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GitCommit:
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int
    insertions: int
    deletions: int
    complexity_score: float

@dataclass
class TilEntry:
    date: str
    title: str
    summary: str
    code_example: str
    tags: List[str]
    complexity: float

class TilSkill:
    """
    Monitors Git history and generates learning notes for complex changes
    """

    def __init__(self, til_file_path: str = './TIL.md'):
        self.til_file_path = til_file_path
        self.git_history: List[GitCommit] = []

    def monitor_recent_changes(self, hours: int = 24) -> Optional[GitCommit]:
        """
        Analyzes recent Git commits and identifies the most complex change
        """
        try:
            # Get recent commits from Git
            since_date = datetime.now() - timedelta(hours=hours)
            date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')

            # Get commit information
            git_log_cmd = ['git', 'log', f'--since="{date_str}"', '--pretty=format:%H|%an|%ad|%s', '--date=iso']
            git_stats_cmd = ['git', 'log', f'--since="{date_str}"', '--numstat', '--pretty=format:""']

            try:
                git_log_output = subprocess.check_output(git_log_cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()

                if not git_log_output:
                    print(f"No commits found in the last {hours} hours")
                    return None

                # Parse git log output
                commits = []
                for line in git_log_output.split('\n'):
                    if '|' in line:
                        parts = line.split('|', 3)  # Split into at most 4 parts
                        if len(parts) >= 4:
                            hash_val, author, date_str_part, message = parts
                            try:
                                date_obj = datetime.strptime(date_str_part, '%Y-%m-%d %H:%M:%S %z')
                            except ValueError:
                                # Fallback for different date formats
                                date_obj = datetime.now()

                            commits.append(GitCommit(
                                hash=hash_val,
                                author=author,
                                date=date_obj,
                                message=message,
                                files_changed=0,
                                insertions=0,
                                deletions=0,
                                complexity_score=0.0
                            ))

                # Get statistics for each commit
                for commit in commits:
                    stats_cmd = ['git', 'show', '--numstat', '--oneline', commit.hash]
                    try:
                        stats_output = subprocess.check_output(stats_cmd, stderr=subprocess.DEVNULL).decode('utf-8')

                        lines = stats_output.strip().split('\n')[1:]  # Skip the first line which is the commit message
                        files_changed = 0
                        insertions = 0
                        deletions = 0

                        for line in lines:
                            if '\t' in line:
                                parts = line.split('\t')
                                if len(parts) >= 2:
                                    try:
                                        ins = parts[0].strip()
                                        dels = parts[1].strip()

                                        if ins != '-':
                                            insertions += int(ins) if ins.isdigit() else 0
                                        if dels != '-':
                                            deletions += int(dels) if dels.isdigit() else 0
                                        files_changed += 1
                                    except ValueError:
                                        continue

                        commit.files_changed = files_changed
                        commit.insertions = insertions
                        commit.deletions = deletions
                        commit.complexity_score = self._calculate_complexity(
                            files_changed, insertions, deletions, commit.message
                        )
                    except subprocess.CalledProcessError:
                        # If we can't get stats for a commit, set defaults
                        commit.files_changed = 0
                        commit.insertions = 0
                        commit.deletions = 0
                        commit.complexity_score = self._calculate_complexity(
                            0, 0, 0, commit.message
                        )

                self.git_history = commits

                # Find the most complex commit
                if commits:
                    most_complex = max(commits, key=lambda c: c.complexity_score)
                    return most_complex if most_complex.complexity_score > 1 else None
                else:
                    return None

            except subprocess.CalledProcessError as e:
                print(f"Git command failed: {e}")
                return None

        except Exception as e:
            print(f"Error monitoring Git changes: {e}")
            return None

    def _calculate_complexity(self, files_changed: int, insertions: int, deletions: int, message: str) -> float:
        """
        Calculate complexity score based on multiple factors
        """
        file_change_weight = 2.0
        insertion_weight = 0.5
        deletion_weight = 0.5
        message_length_weight = 0.1

        complexity = (
            (files_changed * file_change_weight) +
            (insertions * insertion_weight) +
            (deletions * deletion_weight) +
            (len(message) * message_length_weight)
        )

        return complexity

    def generate_til_entry(self, commit: GitCommit) -> TilEntry:
        """
        Generates a TIL entry based on the most complex commit
        """
        try:
            # Get the actual changes from the commit
            diff_cmd = ['git', 'show', '--name-only', commit.hash]
            diff_output = subprocess.check_output(diff_cmd, stderr=subprocess.DEVNULL).decode('utf-8')
            changed_files = [f.strip() for f in diff_output.split('\n')[1:] if f.strip()]

            # Create a summary of what was changed
            summary = self._create_summary_from_commit(commit, changed_files)

            # Get a code example from the commit
            code_example = self._get_code_example_from_commit(commit.hash)

            # Determine tags based on the commit
            tags = self._extract_tags(commit.message, changed_files)

            return TilEntry(
                date=datetime.now().strftime('%Y-%m-%d'),
                title=self._generate_title(commit.message),
                summary=summary,
                code_example=code_example,
                tags=tags,
                complexity=commit.complexity_score
            )
        except Exception as e:
            print(f"Error generating TIL entry: {e}")
            return TilEntry(
                date=datetime.now().strftime('%Y-%m-%d'),
                title="Error processing commit",
                summary=f"Error occurred while processing commit: {e}",
                code_example="",
                tags=["error"],
                complexity=0.0
            )

    def _create_summary_from_commit(self, commit: GitCommit, files: List[str]) -> str:
        """
        Create a summary from the commit information
        """
        file_types = self._get_file_types(files)
        file_type_counts = self._count_file_types(file_types)

        summary = f"Implemented a change that affected {commit.files_changed} files with {commit.insertions} additions and {commit.deletions} deletions. "

        if file_type_counts.get('.py', 0) > 0:
            summary += 'This involved Python code modifications. '
        if file_type_counts.get('.js', 0) > 0 or file_type_counts.get('.ts', 0) > 0:
            summary += 'JavaScript/TypeScript code was updated. '
        if file_type_counts.get('.css', 0) > 0 or file_type_counts.get('.scss', 0) > 0:
            summary += 'Styling changes were included. '
        if file_type_counts.get('.html', 0) > 0:
            summary += 'HTML templates were modified. '

        summary += f'The commit message was: "{commit.message}".'

        return summary

    def _get_code_example_from_commit(self, hash_val: str) -> str:
        """
        Extract a code example from the commit
        """
        try:
            # Get the diff of the commit
            diff_cmd = ['git', 'show', '--unified=3', hash_val]
            diff_output = subprocess.check_output(diff_cmd, stderr=subprocess.DEVNULL).decode('utf-8')

            # Extract code changes (simplified)
            lines = diff_output.split('\n')
            code_lines = []

            for i, line in enumerate(lines):
                if line.startswith('+') or line.startswith('-'):
                    # Include context lines as well
                    if i > 0:
                        code_lines.append(lines[i-1])  # Add context before
                    code_lines.append(line)
                    if i < len(lines) - 1:
                        code_lines.append(lines[i+1])  # Add context after

                    if len(code_lines) >= 10:  # Limit to 10 lines
                        break

            return '\n'.join(code_lines[:10])
        except Exception:
            return 'Could not extract code example from commit.'

    def _get_file_types(self, files: List[str]) -> List[str]:
        """
        Get file extensions from the list of files
        """
        return [os.path.splitext(file)[1] for file in files if '.' in file]

    def _count_file_types(self, file_types: List[str]) -> Dict[str, int]:
        """
        Count occurrences of each file type
        """
        counts = {}
        for file_type in file_types:
            counts[file_type] = counts.get(file_type, 0) + 1
        return counts

    def _extract_tags(self, message: str, files: List[str]) -> List[str]:
        """
        Extract tags based on commit message and files
        """
        tags = []

        lower_message = message.lower()

        if 'fix' in lower_message or 'bug' in lower_message:
            tags.append('bug-fix')
        if 'feat' in lower_message or 'feature' in lower_message:
            tags.append('feature')
        if 'perf' in lower_message or 'optimiz' in lower_message:
            tags.append('performance')
        if 'refactor' in lower_message:
            tags.append('refactoring')
        if 'test' in lower_message:
            tags.append('testing')
        if 'docs' in lower_message or 'doc' in lower_message:
            tags.append('documentation')

        # Add file type tags
        file_types = list(set(self._get_file_types(files)))
        for file_type in file_types:
            if file_type:  # Remove the dot from extension
                tags.append(file_type[1:])

        return list(set(tags))  # Remove duplicates

    def _generate_title(self, message: str) -> str:
        """
        Generate a title from the commit message
        """
        # Clean up the commit message to make a good title
        title = re.sub(r'^[\w]+(\([\w\$\.\-\*]+\))?[\:\s]', '', message)  # Remove conventional commits prefix
        title = title.capitalize()  # Capitalize first letter

        # Limit length
        if len(title) > 60:
            title = title[:57] + '...'

        return title

    def add_to_til(self, entry: TilEntry) -> None:
        """
        Adds a TIL entry to the TIL.md file
        """
        til_content = ''

        # Read existing TIL file if it exists
        if os.path.exists(self.til_file_path):
            with open(self.til_file_path, 'r', encoding='utf-8') as f:
                til_content = f.read()

        # Create the new entry
        new_entry = f"""
## {entry.date}: {entry.title}

**Complexity Score:** {entry.complexity:.1f}/10

**Summary:** {entry.summary}

**Tags:** {', '.join(entry.tags)}

**Code Example:**
```
{entry.code_example}
```

---

"""

        # Prepend the new entry to the content
        updated_content = new_entry + til_content

        # Write back to the file
        with open(self.til_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"TIL entry added to: {self.til_file_path}")

    def run_til_generation(self, hours: int = 24) -> bool:
        """
        Runs the full TIL generation process
        """
        print(f"Monitoring Git changes from the last {hours} hours...")

        most_complex_commit = self.monitor_recent_changes(hours)

        if not most_complex_commit:
            print("No complex changes found to document.")
            return False

        print(f"Found most complex commit: {most_complex_commit.message} (score: {most_complex_commit.complexity_score:.2f})")

        til_entry = self.generate_til_entry(most_complex_commit)
        self.add_to_til(til_entry)

        print("TIL entry generated successfully!")
        return True

    def get_recent_tils(self, limit: int = 5) -> List[TilEntry]:
        """
        Gets recent TIL entries
        """
        if not os.path.exists(self.til_file_path):
            return []

        with open(self.til_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        entries = []
        import re

        # Simple parsing of TIL.md entries
        entry_pattern = r'## (\d{4}-\d{2}-\d{2}): (.+?)\n\*\*Complexity Score:\*\* ([\d.]+)\/10\n\*\*Summary:\*\* (.+?)\n\*\*Tags:\*\* (.+?)\n\*\*Code Example:\*\*\n```(?:\w+)?\n([\s\S]*?)\n```\n---'

        matches = re.findall(entry_pattern, content)

        for match in matches[:limit]:
            date, title, complexity, summary, tags_str, code_example = match
            tags = [tag.strip() for tag in tags_str.split(',')]

            entries.append(TilEntry(
                date=date,
                title=title,
                summary=summary,
                code_example=code_example,
                tags=tags,
                complexity=float(complexity)
            ))

        return entries

# Example usage
if __name__ == "__main__":
    # til_skill = TilSkill('./my-til.md')
    # til_skill.run_til_generation(24)
    pass