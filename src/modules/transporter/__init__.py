# app/utils/__init__.py

import os
import importlib
import pkgutil

# Lấy tên package hiện tại
__all__ = []

# Duyệt tất cả module con trong thư mục hiện tại (không đệ quy)
package_dir = os.path.dirname(__file__)
for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
    if not is_pkg and module_name != "__init__":
        module = importlib.import_module(f".{module_name}", package=__name__)
        
        # Nếu module có biến __all__, import những gì nó khai báo
        if hasattr(module, "__all__"):
            for attr in module.__all__:
                globals()[attr] = getattr(module, attr)
                __all__.append(attr)
        else:
            # Import tất cả public attributes (không bắt đầu bằng _)
            for attr in dir(module):
                if not attr.startswith("_"):
                    globals()[attr] = getattr(module, attr)
                    __all__.append(attr)
