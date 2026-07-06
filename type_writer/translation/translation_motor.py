import struct

def parse_direction(direction:str)->int:
    if(direction=='forward'):
        return 0x00
    elif(direction=='reverse'):
        return 0x01
    else:
        raise ValueError("'forward' or 'reverse'")
    
    

def build_speed_frame(addr: int, direction: str, accel: int, speed_rpm: float) -> str:

    certain_direction=parse_direction(direction)

    data_bytes = bytearray()
    data_bytes.append(certain_direction)
    data_bytes.append(accel)

    speed_bytes = struct.pack('>f', speed_rpm)
    data_bytes.extend(speed_bytes)

    func = 0xF1
    check_sum = (0xC5 + addr + func + sum(data_bytes)) & 0xFF

    frame_str = (
        f"C5"
        f"{addr:02X}"
        f"{func:02X}"
        f"{certain_direction:02X}"
        f"{accel:02X}"
        f"{speed_bytes.hex().upper()}"
        f"{check_sum:02X}"
        f"5C"
    )
    
    return frame_str

def build_abs_pos_frame(addr: int, direction: str, accel: int, speed_rpm: int, position: int) -> str:

    certain_direction=parse_direction(direction)

    data_bytes = bytearray()
    data_bytes.append(certain_direction)
    data_bytes.append(accel)

    speed_bytes = struct.pack('>H', speed_rpm)
    data_bytes.extend(speed_bytes)

    pos_bytes = struct.pack('>I', position)
    data_bytes.extend(pos_bytes)

    func = 0xF2
    check_sum = (0xC5 + addr + func + sum(data_bytes)) & 0xFF

    frame_str = (
        f"C5"
        f"{addr:02X}"
        f"{func:02X}"
        f"{certain_direction:02X}"
        f"{accel:02X}"
        f"{speed_rpm:04X}"
        f"{position:08X}"
        f"{check_sum:02X}"
        f"5C"
    )

    return frame_str

def build_rel_pos_frame(addr: int, direction: str, accel: int, speed_rpm: int, position: int) -> str:

    certain_direction=parse_direction(direction)

    data_bytes = bytearray()
    data_bytes.append(certain_direction)
    data_bytes.append(accel)

    speed_bytes = struct.pack('>H', speed_rpm)
    data_bytes.extend(speed_bytes)

    pos_bytes = struct.pack('>I', position)
    data_bytes.extend(pos_bytes)

    func = 0xF3
    check_sum = (0xC5 + addr + func + sum(data_bytes)) & 0xFF

    frame_str = (
        f"C5"
        f"{addr:02X}"
        f"{func:02X}"
        f"{certain_direction:02X}"
        f"{accel:02X}"
        f"{speed_rpm:04X}"
        f"{position:08X}"
        f"{check_sum:02X}"
        f"5C"
    )

    return frame_str
