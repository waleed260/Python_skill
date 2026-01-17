"""
Test file for the three Python maintenance skills
"""

import os
import tempfile
from legacy_decoder_skill import LegacyDecoderSkill
from api_contract_validator_skill import ApiContractValidator
from til_skill import TilSkill

def test_skills():
    print("Testing Python Maintenance Skills...\n")

    # Test Legacy Decoder Skill
    print("1. Testing Legacy Decoder Skill...")
    try:
        decoder = LegacyDecoderSkill()

        # Create a sample legacy function to analyze
        sample_legacy_code = '''
def complex_legacy_function(input_data, config, options):
    result = {}
    temp = []

    if config and config.get('enabled'):
        for i in range(len(input_data)):
            if input_data[i].get('active'):
                processed = process_item(input_data[i], options)
                temp.append(processed)

                if processed.get('status') == 'error':
                    print('Error processing item: ', input_data[i].get('id'))
                    if not hasattr(globals(), 'errors'):
                        globals()['errors'] = []
                    globals()['errors'].append(input_data[i].get('id'))

        result['items'] = temp
        result['total'] = len(temp)
        result['timestamp'] = __import__('datetime').datetime.now()

        # Make a network request
        import requests
        requests.post('/api/update-stats', json=result)

    return result


def process_item(item, opts):
    return {
        'id': item.get('id'),
        'processed': True,
        'status': 'validated' if opts.get('validate') else 'pending'
    }
'''

        # Write the sample code to a file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(sample_legacy_code)
            temp_file = f.name

        # Analyze the function
        analysis = decoder.analyze_function(temp_file, 'complex_legacy_function')
        print('   ✓ Function analysis completed')
        print(f'   - Parameters: {", ".join(analysis.parameters)}')
        print(f'   - Side effects: {len(analysis.side_effects)} found')
        print(f'   - Data flow mappings: {len(analysis.data_flow)}')

        # Generate explainer
        decoder.generate_explainer_md(analysis, './EXPLAINER_PYTHON.md')
        print('   ✓ EXPLAINER_PYTHON.md generated')

        # Clean up temp file
        os.unlink(temp_file)

    except Exception as e:
        print(f'   ✗ Legacy Decoder test failed: {e}')

    print('\n2. Testing API Contract Validator Skill...')
    try:
        validator = ApiContractValidator()

        # Create sample backend type
        backend_type_code = '''
from typing import Optional, TypedDict

class User(TypedDict):
    id: str
    name: str
    email: str
    created_at: str
    is_active: bool
    profile: Optional["UserProfile"]

class UserProfile(TypedDict):
    bio: Optional[str]
    avatar: str
'''

        # Create sample frontend code
        frontend_code = '''
import requests

def fetch_user(user_id: str):
    response = requests.get(f'/api/users/{user_id}')
    user_data = response.json()

    # Access properties directly (some might not exist in backend)
    user = {
        'id': user_data.get('id'),
        'name': user_data.get('name'),
        'email': user_data.get('email'),
        'created_at': user_data.get('created_at'),
        'is_active': user_data.get('is_active'),
        'bio': user_data.get('bio'),  # This might be a mismatch!
        'avatar': user_data.get('avatar')  # This might be a mismatch!
    }

    return user
'''

        # Write sample files
        with tempfile.NamedTemporaryFile(mode='w', suffix='_backend.py', delete=False) as f:
            f.write(backend_type_code)
            backend_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='_frontend.py', delete=False) as f:
            f.write(frontend_code)
            frontend_file = f.name

        # Validate the contract
        report = validator.validate_contract(
            backend_file,
            frontend_file,
            'User'
        )

        print('   ✓ Contract validation completed')
        print(f'   - Backend type: {report.backend_type}')
        print(f'   - Mismatches found: {len(report.mismatches)}')

        # Generate drift report
        validator.generate_drift_report(report, './SCHEMA_DRIFT_REPORT_PYTHON.md')
        print('   ✓ SCHEMA_DRIFT_REPORT_PYTHON.md generated')

        # Clean up temp files
        os.unlink(backend_file)
        os.unlink(frontend_file)

    except Exception as e:
        print(f'   ✗ API Contract Validator test failed: {e}')

    print('\n3. Testing Self-Documenting TIL Skill...')
    try:
        til_skill = TilSkill('./TIL_PYTHON_TEST.md')

        # Try to run the TIL generation
        # Note: This requires Git to be initialized in the directory
        try:
            import subprocess

            # Initialize git if not already done
            try:
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                subprocess.run(['git', 'config', 'user.name', '"Test User"'], check=True, capture_output=True)
                subprocess.run(['git', 'config', 'user.email', '"test@example.com"'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # Git might already be initialized
                pass

            # Create a test commit to work with
            with open('./test_file_for_til_python.txt', 'w') as f:
                f.write('Test content for Python TIL skill')

            subprocess.run(['git', 'add', './test_file_for_til_python.txt'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', '"feat: Add complex algorithm for data processing"'], check=True, capture_output=True)

            result = til_skill.run_til_generation(1)
            print(f'   ✓ TIL generation completed: {result}')

            # Show recent TILs
            recent_tils = til_skill.get_recent_tils(2)
            print(f'   - Recent TIL entries: {len(recent_tils)}')

            # Clean up test file
            os.remove('./test_file_for_til_python.txt')

        except subprocess.CalledProcessError as git_error:
            print(f'   ⚠ Skipping TIL test (Git error): {git_error}')
        except FileNotFoundError:
            print('   ⚠ Skipping TIL test (Git not installed or not in PATH)')

    except Exception as e:
        print(f'   ✗ TIL Skill test failed: {e}')

    print('\n✓ All Python skill tests completed!')

if __name__ == "__main__":
    test_skills()