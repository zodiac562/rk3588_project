import serial
import time
import struct
import os
from dataclasses import dataclass
from typing import Optional

stall_sign_command=bytes.fromhex('c5012df35c')
position_command=bytes.fromhex('c5012af05c')


    
def read_motor_position(ser: serial.Serial) -> int:

    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        ser.write(position_command)

        response = ser.read(10)
        
        if len(response) < 10:
            print(f"读取数据不完整,期望10字节,实际收到{len(response)}字节")
            return -1

        status_byte = response[3]
        if status_byte == 0x00:
            print("电机返回失败状态(第4字节为00)")
            return -1
        elif status_byte != 0x01:
            print(f"未知状态字节: 0x{status_byte:02X}")
            return -1

        position_bytes = response[4:8]

        position = struct.unpack('>I', position_bytes)[0]
        
        return position
        
    except serial.SerialTimeoutException:
        print("串口读取超时")
        return -1
    except serial.SerialException as e:
        print(f"串口通信错误: {e}")
        return -1
    except Exception as e:
        print(f"未知错误: {e}")
        return -1
    


@dataclass
class OperationResult:
    success: bool
    value: Optional[int]
    code: str
    message: str

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        val = f", value={self.value}" if self.value is not None else ""
        return f"OperationResult({status} | {self.code}{val} | {self.message})"


_MAGIC   = b'\xC5\xA0'
_VERSION = b'\x01'
_HEADER  = _MAGIC + _VERSION
_PAYLOAD_SIZE = 4
_TOTAL_SIZE   = len(_HEADER) + _PAYLOAD_SIZE


def write_position(filename: str, position: int) -> OperationResult:
    if not isinstance(position, int):
        return OperationResult(
            success=False, value=None,
            code="INVALID_TYPE",
            message=f"position 必须为整型，实际类型: {type(position).__name__}"
        )
    if not (0 <= position <= 0xFFFF_FFFF):
        return OperationResult(
            success=False, value=None,
            code="OUT_OF_RANGE",
            message=f"position={position} 超出 uint32 范围 [0, 4294967295]"
        )

    dir_path = os.path.dirname(os.path.abspath(filename)) or "."
    if not os.path.isdir(dir_path):
        return OperationResult(
            success=False, value=None,
            code="INVALID_PATH",
            message=f"目录不存在: {dir_path}"
        )

    if os.path.exists(filename):
        if not os.access(filename, os.W_OK):
            return OperationResult(
                success=False, value=None,
                code="PERMISSION_DENIED",
                message=f"文件无写入权限: {filename}"
            )
    else:
        if not os.access(dir_path, os.W_OK):
            return OperationResult(
                success=False, value=None,
                code="PERMISSION_DENIED",
                message=f"目录无写入权限，无法创建文件: {dir_path}"
            )

    try:
        payload = struct.pack('>I', position)
        data    = _HEADER + payload

        with open(filename, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        return OperationResult(
            success=True, value=None,
            code="WRITE_OK",
            message=f"位置 {position} 已成功写入 {filename}"
        )

    except PermissionError as e:
        return OperationResult(
            success=False, value=None,
            code="PERMISSION_DENIED",
            message=f"写入时权限被拒绝: {e}"
        )
    except OSError as e:
        return OperationResult(
            success=False, value=None,
            code="IO_ERROR",
            message=f"文件 I/O 错误: {e}"
        )
    except Exception as e:
        return OperationResult(
            success=False, value=None,
            code="UNKNOWN_ERROR",
            message=f"未知错误: {e}"
        )


def read_position(filename: str) -> OperationResult:
    if not os.path.exists(filename):
        return OperationResult(
            success=False, value=None,
            code="FILE_NOT_FOUND",
            message=f"文件不存在: {filename}"
        )
    if not os.path.isfile(filename):
        return OperationResult(
            success=False, value=None,
            code="NOT_A_FILE",
            message=f"路径不是普通文件: {filename}"
        )
    if not os.access(filename, os.R_OK):
        return OperationResult(
            success=False, value=None,
            code="PERMISSION_DENIED",
            message=f"文件无读取权限: {filename}"
        )

    file_size = os.path.getsize(filename)
    if file_size != _TOTAL_SIZE:
        return OperationResult(
            success=False, value=None,
            code="INVALID_SIZE",
            message=f"文件大小异常: 期望 {_TOTAL_SIZE} 字节，实际 {file_size} 字节"
        )

    try:
        with open(filename, 'rb') as f:
            data = f.read(_TOTAL_SIZE)

        if len(data) != _TOTAL_SIZE:
            return OperationResult(
                success=False, value=None,
                code="INCOMPLETE_READ",
                message=f"读取不完整: 期望 {_TOTAL_SIZE} 字节，实际 {len(data)} 字节"
            )

        if data[0:2] != _MAGIC:
            return OperationResult(
                success=False, value=None,
                code="MAGIC_MISMATCH",
                message=f"魔数不匹配: 期望 {_MAGIC.hex()}, 实际 {data[0:2].hex()}"
            )

        if data[2:3] != _VERSION:
            return OperationResult(
                success=False, value=None,
                code="VERSION_MISMATCH",
                message=f"版本不匹配: 期望 {_VERSION.hex()}, 实际 {data[2:3].hex()}"
            )

        position = struct.unpack('>I', data[3:7])[0]

        return OperationResult(
            success=True, value=position,
            code="READ_OK",
            message=f"成功读取位置: {position}"
        )

    except PermissionError as e:
        return OperationResult(
            success=False, value=None,
            code="PERMISSION_DENIED",
            message=f"读取时权限被拒绝: {e}"
        )
    except struct.error as e:
        return OperationResult(
            success=False, value=None,
            code="UNPACK_ERROR",
            message=f"数据解包失败（格式损坏）: {e}"
        )
    except OSError as e:
        return OperationResult(
            success=False, value=None,
            code="IO_ERROR",
            message=f"文件 I/O 错误: {e}"
        )
    except Exception as e:
        return OperationResult(
            success=False, value=None,
            code="UNKNOWN_ERROR",
            message=f"未知错误: {e}"
        )


if __name__ == "__main__":
    import tempfile

    TEST_CASES = [
        ("正常位置",        512000),
        ("最小值",          0),
        ("最大值",          0xFFFF_FFFF),
        ("中间值",          1_000_000),
    ]

    print("=" * 60)
    print("【写入 / 读取 往返测试】")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        for label, pos in TEST_CASES:
            path = os.path.join(tmpdir, f"pos_{pos}.bin")

            w = write_position(path, pos)
            r = read_position(path)

            ok = r.success and r.value == pos
            print(f"  [{label:8s}] pos={pos:<12d} write={w.code:<14s} "
                  f"read={r.code:<10s} match={'✓' if ok else '✗'}")

        print()
        print("异常场景测试")
        print("-" * 60)

        # 类型错误
        r = write_position(os.path.join(tmpdir, "x.bin"), 3.14)  # type: ignore
        print(f"  浮点数写入:   {r}")

        # 超出范围
        r = write_position(os.path.join(tmpdir, "x.bin"), -1)
        print(f"  负数写入:     {r}")

        # 路径不存在
        r = write_position("/nonexistent_dir/pos.bin", 100)
        print(f"  无效目录:     {r}")

        # 读取不存在文件
        r = read_position(os.path.join(tmpdir, "ghost.bin"))
        print(f"  读取不存在:   {r}")

        # 写入损坏数据后读取
        corrupt = os.path.join(tmpdir, "corrupt.bin")
        with open(corrupt, 'wb') as f:
            f.write(b'\xDE\xAD\xBE\xEF\x00\x00\x00')   # 魔数错误
        r = read_position(corrupt)
        print(f"  魔数不匹配:   {r}")

        # 文件大小异常
        short = os.path.join(tmpdir, "short.bin")
        with open(short, 'wb') as f:
            f.write(b'\xC5\xA0\x01')                    # 只有3字节
        r = read_position(short)
        print(f"  文件过短:     {r}")
