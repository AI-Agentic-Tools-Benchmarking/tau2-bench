
import sys
import gc
import ctypes
import psutil
import os
from typing import Any

def get_object_info(obj: Any, name: str = "object") -> dict:
    """Get storage location and size info for an object and its attributes."""
    
    info = {
        "name": name,
        "type": type(obj).__name__,
        "memory_address": hex(id(obj)),
        "size_bytes": sys.getsizeof(obj),
        "storage": "RAM (CPU)",
        "attributes": {}
    }
    
    # Try to get GPU info if it's a tensor
    try:
        import torch
        if isinstance(obj, torch.Tensor):
            info["storage"] = f"GPU VRAM ({obj.device})" if obj.is_cuda else "RAM (CPU)"
            info["size_bytes"] = obj.element_size() * obj.nelement()
            info["dtype"] = str(obj.dtype)
            info["shape"] = list(obj.shape)
    except ImportError:
        pass
    
    # Inspect class instance attributes
    if hasattr(obj, "__dict__"):
        total_attr_size = 0
        for attr_name, attr_val in vars(obj).items():
            attr_info = {
                "type": type(attr_val).__name__,
                "memory_address": hex(id(attr_val)),
                "size_bytes": get_deep_size(attr_val),
                "storage": "RAM (CPU)",
            }
            
            # Check if attribute is a tensor on GPU
            try:
                import torch
                if isinstance(attr_val, torch.Tensor):
                    attr_info["storage"] = f"GPU VRAM ({attr_val.device})" if attr_val.is_cuda else "RAM (CPU)"
                    attr_info["size_bytes"] = attr_val.element_size() * attr_val.nelement()
                    attr_info["dtype"] = str(attr_val.dtype)
                    attr_info["shape"] = list(attr_val.shape)
            except ImportError:
                pass
            
            total_attr_size += attr_info["size_bytes"]
            info["attributes"][attr_name] = attr_info
        
        info["total_size_bytes"] = sys.getsizeof(obj) + total_attr_size
    else:
        info["total_size_bytes"] = info["size_bytes"]
    
    return info


def get_deep_size(obj: Any, seen: set = None) -> int:
    """Recursively get total memory size of an object."""
    if seen is None:
        seen = set()
    
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    
    size = sys.getsizeof(obj)
    
    if isinstance(obj, dict):
        size += sum(get_deep_size(k, seen) + get_deep_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(get_deep_size(item, seen) for item in obj)
    elif hasattr(obj, "__dict__"):
        size += get_deep_size(vars(obj), seen)
    
    return size


def print_object_report(obj: Any, name: str = "MyObject"):
    """Pretty print the full storage report."""
    info = get_object_info(obj, name)
    
    print(f"\n{'='*55}")
    print(f"  Object Report: {info['name']}")
    print(f"{'='*55}")
    print(f"  Type            : {info['type']}")
    print(f"  Memory Address  : {info['memory_address']}")
    print(f"  Storage         : {info['storage']}")
    print(f"  Object Size     : {format_size(info['size_bytes'])}")
    print(f"  Total Size      : {format_size(info['total_size_bytes'])}")
    
    if info["attributes"]:
        print(f"\n  {'Attribute':<20} {'Type':<15} {'Address':<14} {'Size':<12} Storage")
        print(f"  {'-'*20} {'-'*15} {'-'*14} {'-'*12} {'-'*15}")
        for attr_name, attr in info["attributes"].items():
            extra = f" shape={attr.get('shape')}" if "shape" in attr else ""
            print(f"  {attr_name:<20} {attr['type']:<15} {attr['memory_address']:<14} "
                  f"{format_size(attr['size_bytes']):<12} {attr['storage']}{extra}")
    
    print(f"{'='*55}\n")
    
    # System RAM snapshot
    process = psutil.Process(os.getpid())
    ram_used = process.memory_info().rss
    print(f"  Process RAM usage : {format_size(ram_used)}")
    
    # GPU snapshot
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i)
                reserved  = torch.cuda.memory_reserved(i)
                print(f"  GPU {i} Allocated  : {format_size(allocated)}")
                print(f"  GPU {i} Reserved   : {format_size(reserved)}")
    except ImportError:
        pass
    
    print()


def format_size(size_bytes: int) -> str:
    """Human-readable byte size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"
