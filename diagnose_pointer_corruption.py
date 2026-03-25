#!/usr/bin/env python3
"""
Diagnostic script to check for pointer corruption in character table.
"""
import sys
import os
import struct

def check_pointer_values(data_bytes, entry_size, offset):
    """Check if pointers in the data are valid GBA addresses."""
    print(f"\nChecking pointers at offset {hex(offset)}...")
    
    pointers = []
    for i in range(0, len(data_bytes), entry_size):
        entry = data_bytes[i:i+entry_size]
        if len(entry) < entry_size:
            break
        
        # Read name_pointer (offset 0, 4 bytes)
        name_ptr = struct.unpack_from('<I', entry, 0)[0]
        # Read desc_pointer (offset 4, 4 bytes)
        desc_ptr = struct.unpack_from('<I', entry, 4)[0]
        
        char_idx = struct.unpack_from('<H', entry, 8)[0]
        
        # Check if pointers are valid GBA ROM addresses
        # Valid GBA ROM range: 0x08000000 to 0x09FFFFFF (for ROM)
        # 0xFFFF... values are invalid
        
        if name_ptr == 0 or name_ptr == 0xFFFFFFFF or name_ptr == 0xFFFFFFFE:
            print(f"  ❌ Character {char_idx}: Invalid name_pointer = {hex(name_ptr)}")
            pointers.append(('name', char_idx, name_ptr))
        
        if desc_ptr == 0 or desc_ptr == 0xFFFFFFFF or desc_ptr == 0xFFFFFFFE:
            print(f"  ❌ Character {char_idx}: Invalid desc_pointer = {hex(desc_ptr)}")
            pointers.append(('desc', char_idx, desc_ptr))
        
        # Check if pointer is in reasonable ROM range
        if name_ptr != 0 and not (0x08000000 <= name_ptr <= 0x09FFFFFF):
            print(f"  ⚠ Character {char_idx}: Suspicious name_pointer = {hex(name_ptr)}")
            pointers.append(('name', char_idx, name_ptr))
        
        if desc_ptr != 0 and not (0x08000000 <= desc_ptr <= 0x09FFFFFF):
            print(f"  ⚠ Character {char_idx}: Suspicious desc_pointer = {hex(desc_ptr)}")
            pointers.append(('desc', char_idx, desc_ptr))
    
    if not pointers:
        print("  ✓ All pointers look valid")
    
    return pointers

def analyze_potential_corruption(data_before, data_after, entry_size):
    """Compare data before and after to find corruption."""
    print("\n" + "="*60)
    print("CORRUPTION ANALYSIS")
    print("="*60)
    
    if len(data_before) != len(data_after):
        print(f"❌ Size mismatch: before={len(data_before)} bytes, after={len(data_after)} bytes")
        return
    
    changes = []
    for i in range(0, min(len(data_before), len(data_after)), entry_size):
        entry_before = data_before[i:i+entry_size]
        entry_after = data_after[i:i+entry_size]
        
        if entry_before == entry_after:
            continue
        
        # Check pointer changes
        ptr_before_0 = struct.unpack_from('<I', entry_before, 0)[0]
        ptr_after_0 = struct.unpack_from('<I', entry_after, 0)[0]
        
        ptr_before_4 = struct.unpack_from('<I', entry_before, 4)[0]
        ptr_after_4 = struct.unpack_from('<I', entry_after, 4)[0]
        
        char_id = struct.unpack_from('<H', entry_after, 8)[0]
        
        if ptr_before_0 != ptr_after_0:
            changes.append(f"Character {char_id}: name_pointer {hex(ptr_before_0)} -> {hex(ptr_after_0)}")
        
        if ptr_before_4 != ptr_after_4:
            changes.append(f"Character {char_id}: desc_pointer {hex(ptr_before_4)} -> {hex(ptr_after_4)}")
    
    if changes:
        print("\n⚠ Found pointer changes:")
        for change in changes:
            print(f"  {change}")
    else:
        print("\n✓ No pointer corruption detected")

if __name__ == "__main__":
    print("Pointer Corruption Diagnostic Tool")
    print("="*60)
    print("\nThis tool helps identify pointer corruption issues.")
    print("\nTo use:")
    print("1. Save original character table data before randomization")
    print("2. Save randomized character table data after randomization")
    print("3. Run: python diagnose_pointer_corruption.py")
    print("\nExample integration:")
    print("  - Call check_pointer_values() on loaded table data")
    print("  - Call analyze_potential_corruption() before/after randomization")