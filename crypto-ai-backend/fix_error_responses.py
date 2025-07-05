#!/usr/bin/env python3
"""
Script to fix error responses for production safety
This will update error handling to not expose sensitive information
"""
import re
import os

def fix_error_responses(file_path):
    """Fix error responses in a Python file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Pattern 1: Fix jsonify({'error': str(e)})
    pattern1 = r"return jsonify\({'error': str\(e\)}\), (\d+)"
    replacement1 = r"logger.error(f'Error occurred: {str(e)}', exc_info=True)\n        if current_app.config.get('ENV') == 'production':\n            return jsonify({'error': 'An error occurred processing your request'}), \1\n        else:\n            return jsonify({'error': str(e)}), \1"
    
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        changes_made.append("Fixed error message exposure")
    
    # Pattern 2: Fix traceback.print_exc()
    pattern2 = r"traceback\.print_exc\(\)"
    replacement2 = r"logger.error('Exception occurred', exc_info=True)"
    
    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement2, content)
        changes_made.append("Fixed traceback exposure")
    
    # Pattern 3: Fix print statements with sensitive info
    sensitive_prints = [
        (r"print\(f['\"].*api_key.*['\"].*\)", "logger.debug('Processing API request')"),
        (r"print\(f['\"].*password.*['\"].*\)", "logger.debug('Processing authentication')"),
        (r"print\(f['\"].*secret.*['\"].*\)", "logger.debug('Processing secure data')"),
    ]
    
    for pattern, replacement in sensitive_prints:
        if re.search(pattern, content, re.IGNORECASE):
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            changes_made.append("Fixed sensitive print statements")
    
    # Only write if changes were made
    if content != original_content:
        # Backup original
        backup_path = file_path + '.backup'
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✓ Fixed {file_path}: {', '.join(changes_made)}")
        return True
    else:
        print(f"  No changes needed in {file_path}")
        return False

def main():
    """Fix error responses in all Python files"""
    print("=== Fixing Error Responses for Production Safety ===\n")
    
    # Files to check
    files_to_fix = [
        'app.py',
        'strategies/technical/trendline_breakout.py',
        'strategies/technical/rsi_strategy.py',
        'strategies/technical/ma_crossover_strategy.py',
        'strategies/technical/bollinger_bands_strategy.py',
        'strategies/technical/volume_spike_strategy.py',
        'strategies/technical/reversal_patterns_strategy.py',
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_error_responses(file_path):
                fixed_count += 1
        else:
            print(f"✗ File not found: {file_path}")
    
    print(f"\n=== Summary ===")
    print(f"Fixed {fixed_count} files")
    print("\nIMPORTANT: Review the changes and test thoroughly!")
    print("Backup files created with .backup extension")
    
    # Create production error handling guide
    with open('PRODUCTION_ERROR_HANDLING.md', 'w') as f:
        f.write("""# Production Error Handling Guide

## Error Response Standards

### 1. Never Expose Internal Details
```python
# BAD - Exposes internal error details
return jsonify({'error': str(e)}), 500

# GOOD - Generic message for production
logger.error(f'Error in endpoint: {str(e)}', exc_info=True)
if current_app.config.get('ENV') == 'production':
    return jsonify({'error': 'An error occurred processing your request'}), 500
else:
    return jsonify({'error': str(e)}), 500
```

### 2. Log Errors Properly
```python
# BAD - Prints to console
print(f"Error: {e}")
traceback.print_exc()

# GOOD - Uses logger
logger.error('Error occurred', exc_info=True)
```

### 3. Sanitize Error Messages
```python
from utils.error_handlers import sanitize_error_message

# Sanitize any user-facing error messages
safe_message = sanitize_error_message(str(error))
return jsonify({'error': safe_message}), 400
```

### 4. Standard Error Response Format
```json
{
    "success": false,
    "error": "Generic Error Type",
    "message": "User-friendly message without technical details"
}
```

### 5. Error Categories

| Error Type | HTTP Code | User Message |
|------------|-----------|--------------|
| Validation | 400 | "Invalid input provided" |
| Auth | 401 | "Authentication required" |
| Permission | 403 | "Permission denied" |
| Not Found | 404 | "Resource not found" |
| Server | 500 | "An error occurred processing your request" |

### 6. Debugging in Production

- Check logs at `/logs/error.log` for full error details
- Use correlation IDs to track requests
- Monitor error rates in your APM tool
- Never enable debug mode in production
""")
    
    print("\nCreated PRODUCTION_ERROR_HANDLING.md with guidelines")

if __name__ == "__main__":
    main()