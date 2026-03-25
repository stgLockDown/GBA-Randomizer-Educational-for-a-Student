# Story Breakage Troubleshooting Guide

## Problem: Story sequences hang on black screen

If you're experiencing black screens during story sequences after randomization, this guide will help you identify and fix the issue.

## Common Causes and Solutions

### 1. Class Randomization Breaking Story Scripts
**Symptoms**: Black screen immediately after starting new game or during cutscenes

**Cause**: Changing lord classes or required character classes can break scripted events that depend on specific class IDs.

**Solution**:
- Use the **"Story Safe"** preset (recommended for first playthrough)
- Or manually set `class_mode` to `vanilla` in settings
- Ensure `keep_lords` is set to `true`

### 2. Invalid Class IDs
**Symptoms**: Game crashes when trying to load character sprites

**Cause**: Randomization assigned class IDs outside valid range (0-127)

**Solution**:
- Check the **Safety** tab for validation errors
- Enable `auto_fix` in settings to automatically fix invalid IDs
- Reduce `max_class_copies` to prevent ID conflicts

### 3. Corrupted Character Pointers
**Symptoms**: Story scripts fail to find character data

**Cause**: Name pointers or portrait pointers corrupted to 0 or invalid addresses

**Solution**:
- Use `class_mode: vanilla` to avoid modifying pointer fields
- Never randomize if validation shows "null pointer" errors
- Rebuild ROM from clean source

### 4. Stat Overflow/Underflow
**Symptoms**: Unexpected character behavior, crashes during stat calculations

**Cause**: Stats randomized outside valid ranges (bases: -20 to 60, growths: 0 to 255)

**Solution**:
- Reduce `bases_variance` and `growths_variance` settings
- Enable `bases_preserve_total` and `growths_preserve_total`
- Set appropriate `bases_min/max` and `growths_min/max`

### 5. Inventory Issues
**Symptoms**: Characters cannot use starting items, scripted events fail

**Cause**: Randomized inventory without ensuring weapon rank compatibility

**Solution**:
- Set `inventory_mode` to `dont_change` or `guarantee_usable`
- Keep `ranks_mode` as `vanilla` for story-critical characters
- Check Safety tab for weapon usability warnings

## Recommended Presets for Story Safety

### Option 1: Story Safe (Most Conservative)
```json
{
  "class_mode": "vanilla",
  "keep_lords": true,
  "bases_variance": 1,
  "growths_variance": 5,
  "inventory_mode": "dont_change"
}
```
**Use when**: Story is completely broken and you want guaranteed stability

### Option 2: Casual (Light Randomization)
```json
{
  "class_mode": "shuffle",
  "keep_lords": true,
  "bases_variance": 2,
  "growths_variance": 10,
  "inventory_mode": "guarantee_usable"
}
```
**Use when**: You want some randomization but need story to work

### Option 3: Vanilla+ (Stats Only)
```json
{
  "class_mode": "vanilla",
  "bases_mode": "random",
  "growths_mode": "random",
  "inventory_mode": "dont_change"
}
```
**Use when**: You want stat variety without breaking anything

## Diagnostic Steps

1. **Check Validation Tab**
   - Look for ERROR level issues (not warnings)
   - Pay attention to "required" and "class" categories
   - Enable `auto_fix` and rebuild if errors present

2. **Try Story Safe Preset**
   - Select "Story Safe" from preset dropdown
   - Build with minimal randomization
   - Test if story works
   - Gradually increase randomization if it works

3. **Review Spoiler Log**
   - Check what was actually randomized
   - Verify lord classes weren't changed
   - Ensure no invalid IDs in character table

4. **Test Different Games**
   - Try FE6, FE7, and FE8 separately
   - Some games may be more sensitive to changes
   - Skill System hacks may have different requirements

## Advanced Troubleshooting

### Check ROM Integrity
Before randomizing, verify:
- Clean ROM (no previous randomizations)
- Correct region (US/EU/JP)
- No other hacks applied

### Isolate the Issue
Test each randomization type separately:
1. Build with only class randomization
2. Build with only stat randomization
3. Build with only inventory randomization

This helps identify which feature is causing the issue.

### Contact Support
If none of these solutions work:
1. Export your settings using the Share button
2. Include the spoiler log
3. Note which game/version you're using
4. Describe exactly where the story breaks

## Prevention Tips

- Always start with a clean ROM
- Use validation and auto-fix features
- Test with conservative presets first
- Keep backups of working configurations
- Read the Safety tab before building