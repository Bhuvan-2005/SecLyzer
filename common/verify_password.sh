#!/bin/bash
# Password verification helper for SecLyzer
# Used by control script and uninstaller

verify_password() {
    local password_file="${1:-/etc/seclyzer/.password_hash}"
    
    if [ ! -f "$password_file" ]; then
        echo "Error: Password file not found. SecLyzer may not be installed properly."
        return 1
    fi
    
    local stored_hash=$(cat "$password_file")
    
    # Prompt for password
    read -s -p "Enter SecLyzer password: " entered_password
    echo ""
    
    # Hash entered password
    local entered_hash=$(echo -n "$entered_password" | sha256sum | cut -d' ' -f1)
    
    # Compare hashes
    if [ "$entered_hash" == "$stored_hash" ]; then
        return 0  # Success
    else
        return 1  # Failure
    fi
}

# Export function if sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    export -f verify_password
fi
