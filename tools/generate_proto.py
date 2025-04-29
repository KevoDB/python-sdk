#!/usr/bin/env python3
"""
Generate Python protobuf code from .proto files in the Kevo project.
This script should be run from the python-sdk directory.

Example usage:
    python tools/generate_proto.py
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Generate Python code from .proto files."""
    # Setup paths
    python_sdk_dir = Path(os.getcwd())
    # Use the proto file from the python-sdk directory
    proto_file = python_sdk_dir / "proto" / "kevo" / "service.proto"
    
    # Ensure we're in the python-sdk directory
    if python_sdk_dir.name != "python-sdk":
        print("Error: This script must be run from the python-sdk directory")
        sys.exit(1)
    
    # Generate protobuf code directly into the kevo directory
    output_dir = python_sdk_dir / "kevo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Run protoc compiler
    try:
        print(f"Generating Python code from {proto_file}...")
        
        # Run protoc command
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={python_sdk_dir}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            str(proto_file),
        ]
        
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Create an __init__.py file in the proto directory that was created
        proto_dir = output_dir / "proto"
        if proto_dir.exists():
            with open(proto_dir / "__init__.py", "w") as f:
                f.write('"""Generated protobuf code."""\n')
            
            # Also ensure the proto/kevo directory has an __init__.py
            kevo_dir = proto_dir / "kevo"
            if kevo_dir.exists():
                with open(kevo_dir / "__init__.py", "w") as f:
                    f.write('"""Generated protobuf code for kevo."""\n')
                
                # Fix import in the generated grpc file
                grpc_file = kevo_dir / "service_pb2_grpc.py"
                if grpc_file.exists():
                    with open(grpc_file, "r") as f:
                        content = f.read()
                    
                    # Fix the import
                    content = content.replace(
                        "from proto.kevo import service_pb2",
                        "from . import service_pb2"
                    )
                    
                    with open(grpc_file, "w") as f:
                        f.write(content)
        
        print("Proto files generated successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Error running protoc: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()