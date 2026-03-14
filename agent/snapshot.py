import os
import shutil
import json
from datetime import datetime


SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "snapshots")


SNAPSHOT_INDEX = os.path.join(SNAPSHOTS_DIR, "index.json")


def _ensure_snapshots_dir():
    """Create snapshots directory if it doesn't exist."""
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def _load_index() -> list[dict]:
    """
    Load the snapshot index from disk.
    The index is a list of snapshot records in chronological order.
    """
    if not os.path.exists(SNAPSHOT_INDEX):
        return []
    try:
        with open(SNAPSHOT_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(index: list[dict]):
    """Save the snapshot index to disk."""
    with open(SNAPSHOT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def take_snapshot(file_path: str) -> str:
    """
    Save a copy of a file before it gets modified.
    Called automatically by write_file, replace_block, append_to_file.

    Args:
        file_path: Absolute path to the file to snapshot

    Returns:
        Snapshot ID string e.g. "snap_003"
    """
    _ensure_snapshots_dir()

    index = _load_index()
    snap_number = len(index) + 1
    snap_id = f"snap_{snap_number:03d}"

    # Build snapshot filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.basename(file_path)
    snap_filename = f"{snap_id}__{filename}__{timestamp}{os.path.splitext(filename)[1]}"
    snap_path = os.path.join(SNAPSHOTS_DIR, snap_filename)

    # Copy the file to snapshots directory
    shutil.copy2(file_path, snap_path)

    # Record in index
    index.append({
        "id":            snap_id,
        "original_path": file_path,
        "snapshot_path": snap_path,
        "filename":      filename,
        "timestamp":     datetime.now().isoformat(),
        "snap_number":   snap_number,
    })
    _save_index(index)

    return snap_id


def rollback(file_path: str = None, snap_id: str = None) -> str:
    """
    Restore a file to a previous snapshot.
    Can roll back by file path (most recent snapshot of that file)
    or by specific snapshot ID.

    Args:
        file_path: Restore the most recent snapshot of this file
        snap_id:   Restore a specific snapshot by ID e.g. "snap_003"

    Returns:
        Success or error message
    """
    index = _load_index()

    if not index:
        return "No snapshots found. Nothing to roll back."

    target = None

    if snap_id:
        # Find specific snapshot by ID
        matches = [s for s in index if s["id"] == snap_id]
        if not matches:
            return f"Error: Snapshot '{snap_id}' not found."
        target = matches[0]

    elif file_path:
        # Find most recent snapshot of this specific file
        matches = [
            s for s in index
            if os.path.normpath(s["original_path"]) == os.path.normpath(file_path)
        ]
        if not matches:
            return f"Error: No snapshots found for '{file_path}'."
        target = matches[-1]  # Most recent

    else:
        # No arguments — roll back the most recent snapshot of any file
        target = index[-1]

    # Restore the file
    try:
        shutil.copy2(target["snapshot_path"], target["original_path"])
        return (
            f"Rolled back '{target['filename']}' to snapshot {target['id']} "
            f"from {target['timestamp'][:19].replace('T', ' ')} ✓"
        )
    except FileNotFoundError:
        return (
            f"Error: Snapshot file missing for {target['id']}. "
            f"It may have been deleted."
        )
    except Exception as e:
        return f"Error restoring snapshot: {e}"


def list_snapshots(file_path: str = None) -> str:
    """
    List all snapshots, optionally filtered by file.
    Called when user asks 'what can I roll back?' or 'show my snapshots'.

    Args:
        file_path: Optional — filter snapshots to just this file

    Returns:
        Formatted string listing all matching snapshots
    """
    index = _load_index()

    if not index:
        return "No snapshots found."

    if file_path:
        index = [
            s for s in index
            if os.path.normpath(s["original_path"]) == os.path.normpath(file_path)
        ]
        if not index:
            return f"No snapshots found for '{file_path}'."

    lines = ["Available snapshots:"]
    for snap in reversed(index):  # Most recent first
        lines.append(
            f"  {snap['id']}  {snap['filename']:<30} "
            f"{snap['timestamp'][:19].replace('T', ' ')}"
        )

    return "\n".join(lines)


def clear_snapshots(confirm: bool = False) -> str:
    """
    Delete all snapshots. Used at end of session to clean up.

    Args:
        confirm: Must be True to actually delete — safety guard

    Returns:
        Success or error message
    """
    if not confirm:
        return "Pass confirm=True to clear all snapshots."

    index = _load_index()
    count = len(index)

    try:
        for snap in index:
            if os.path.exists(snap["snapshot_path"]):
                os.remove(snap["snapshot_path"])

        _save_index([])
        return f"Cleared {count} snapshots."

    except Exception as e:
        return f"Error clearing snapshots: {e}"