#!/usr/bin/env python3
"""
Diagnostic script to identify potential causes of story crashes.
Run this after randomization to check for common issues.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.rom.tables import TableManager
from src.core.validation import ValidationEngine
from src.core.engine import RandomizerSettings

def diagnose_character_table(table_manager, profile):
    """Check for issues that could break story sequences."""
    issues = []
    
    char_table = table_manager.tables.get('characters')
    class_table = table_manager.tables.get('classes')
    item_table = table_manager.tables.get('items')
    
    if not char_table:
        issues.append("CRITICAL: Character table not loaded!")
        return issues
    
    char_meta = profile.get('characters', {})
    rules = profile.get('rules', {})
    
    lord_ids = set(rules.get('lord_character_ids', []))
    required_ids = set(rules.get('required_character_ids', []))
    
    max_class_id = class_table.entries[-1].index if class_table and class_table.entries else 127
    
    print("\n" + "="*60)
    print("STORY SAFETY DIAGNOSTIC REPORT")
    print("="*60)
    
    # Check 1: Lord character integrity
    print("\n[1] Checking Lord Characters...")
    for cid in lord_ids:
        for entry in char_table:
            if entry.get('char_id', entry.index) == cid:
                class_id = entry.get('class_id', 0)
                name = char_meta.get(str(cid), {}).get('name', f'Char_{cid}')
                
                # Check class ID validity
                if class_id < 0 or class_id > max_class_id:
                    issues.append(f"CRITICAL: Lord {name} (ID {cid}) has invalid class ID {class_id}")
                    print(f"  ❌ {name}: Invalid class ID {class_id}")
                else:
                    print(f"  ✓ {name}: Class ID {class_id} (valid)")
                
                # Check for corrupted pointers
                name_ptr = entry.get('name_pointer', 0)
                if name_ptr == 0:
                    issues.append(f"WARNING: Lord {name} (ID {cid}) has null name pointer")
                    print(f"  ⚠ {name}: Null name pointer (may break story)")
                else:
                    print(f"  ✓ {name}: Name pointer {hex(name_ptr)}")
                
                break
    
    # Check 2: Required character integrity
    print("\n[2] Checking Required Characters...")
    for cid in required_ids:
        for entry in char_table:
            if entry.get('char_id', entry.index) == cid:
                class_id = entry.get('class_id', 0)
                name = char_meta.get(str(cid), {}).get('name', f'Char_{cid}')
                
                if class_id < 0 or class_id > max_class_id:
                    issues.append(f"CRITICAL: Required {name} (ID {cid}) has invalid class ID {class_id}")
                    print(f"  ❌ {name}: Invalid class ID {class_id}")
                else:
                    print(f"  ✓ {name}: Class ID {class_id}")
                break
    
    # Check 3: Stat bounds
    print("\n[3] Checking Stat Bounds...")
    for entry in char_table:
        cid = entry.get('char_id', entry.index)
        if str(cid) not in char_meta:
            continue
        
        bases = entry.get_stat_values('bases')
        growths = entry.get_stat_values('growths')
        name = char_meta.get(str(cid), {}).get('name', f'Char_{cid}')
        
        # Check growth bounds
        for stat, val in growths.items():
            if val < 0 or val > 255:
                issues.append(f"ERROR: {name} has growth {stat} = {val} (invalid range)")
                print(f"  ❌ {name}: Growth {stat} = {val} (out of range [0,255])")
        
        # Check base bounds
        for stat, val in bases.items():
            if val < -20 or val > 60:
                issues.append(f"WARNING: {name} has base {stat} = {val} (unusual range)")
                print(f"  ⚠ {name}: Base {stat} = {val} (unusual range [-20,60])")
    
    if not any('base' in issue.lower() or 'growth' in issue.lower() for issue in issues):
        print("  ✓ All stats within valid ranges")
    
    # Check 4: Inventory issues
    print("\n[4] Checking Inventory...")
    for entry in char_table:
        cid = entry.get('char_id', entry.index)
        if str(cid) not in char_meta:
            continue
        
        items = entry.get_stat_values('items')
        name = char_meta.get(str(cid), {}).get('name', f'Char_{cid}')
        
        # Check for invalid item IDs
        for slot, item_id in items.items():
            if item_id < 0 or item_id > 255:
                issues.append(f"ERROR: {name} has invalid item ID {item_id} in {slot}")
                print(f"  ❌ {name}: Invalid item ID {item_id}")
    
    if not any('item' in issue.lower() for issue in issues):
        print("  ✓ All items valid")
    
    # Check 5: Class table integrity
    if class_table:
        print("\n[5] Checking Class Table Integrity...")
        for entry in class_table:
            cid = entry.index
            name_ptr = entry.get('name_ptr', 0)
            
            if name_ptr == 0:
                issues.append(f"WARNING: Class {cid} has null name pointer")
                print(f"  ⚠ Class {cid}: Null name pointer")
        
        print("  ✓ All other classes have valid pointers")
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    if issues:
        print(f"\nFound {len(issues)} potential issues:")
        for i, issue in enumerate(issues, 1):
            severity = "CRITICAL" if "CRITICAL" in issue else ("ERROR" if "ERROR" in issue else "WARNING")
            print(f"  {i}. [{severity}] {issue}")
    else:
        print("\n✅ No issues found! The randomization should be story-safe.")
    
    print("="*60)
    
    return issues

if __name__ == "__main__":
    print("Story Issue Diagnostic Tool")
    print("This script helps identify what might be causing story crashes.")
    
    # This would need actual ROM data to run
    print("\nTo use this tool:")
    print("1. Run the randomizer on your ROM")
    print("2. Load the randomized ROM with TableManager")
    print("3. Call diagnose_character_table(table_manager, profile)")
    print("\nExample usage will be integrated into the main app.")