"""
Reads indexed UNIX fortune files and outputs a fortune cookie.

Fortune index files contain the following header:
typedef struct {                                /* information table */
#define VERSION         2
        u_int32_t       str_version;            /* version number */
        u_int32_t       str_numstr;             /* # of strings in the file */
        u_int32_t       str_longlen;            /* length of longest string */
        u_int32_t       str_shortlen;           /* length of shortest string */
#define STR_RANDOM      0x1                     /* randomized pointers */
#define STR_ORDERED     0x2                     /* ordered pointers */
#define STR_ROTATED     0x4                     /* rot-13'd text */
        u_int32_t       str_flags;              /* bit field for flags */
        u_int8_t        stuff[4];               /* long aligned space */
#define str_delim       stuff[0]                /* delimiting character */
} STRFILE;
"""
import codecs
import struct
import random
from pathlib import Path
from typing import List
from dataclasses import dataclass
from tama import api

fortunes: List["FortuneFile"] = []


@dataclass
class FortuneFile:
    name: str
    total: int
    # Note: the last offset leads an empty string
    offsets: List[int]
    data: bytes
    rotated: bool


@api.on_load()
def load_fortunes(config: dict = None):
    if config is None:
        raise Exception("No config provided")
    idx_paths = [Path(p) for p in config["fortune_paths"]]
    indexes = [
        idx for p in idx_paths for idx in p.iterdir()
        if idx.suffix == ".dat"
    ]
    for idx in indexes:
        datafile = Path(str(idx)[:-4])
        with idx.open("rb") as dat:
            hdr = struct.unpack(">IIIIIcxxx", dat.read(24))
            version, numstr, longlen, shortlen, flags, delim = hdr
            f_random = flags & 0x1
            f_ordered = flags & 0x2
            f_rotated = flags & 0x4
            offsets = []
            for i in range(numstr+1):
                offset, = struct.unpack(">I", dat.read(4))
                offsets.append(offset)
        with datafile.open("rb") as db:
            data = db.read()
        fortunes.append(FortuneFile(
            name=idx.stem, total=numstr, offsets=offsets, data=data,
            rotated=bool(f_rotated)
        ))


def get_fortune() -> str:
    # FIXME: Conditional probability means this will make smaller file fortunes
    # much more prevalent. Make a fairer random choice.
    file: FortuneFile = random.choice(fortunes)
    return get_fortune_from_file(file)


def get_fortune_from_file(file: FortuneFile) -> str:
    # We don't want to get the last index as it's empty
    rand = random.randint(0, file.total-1)
    idx, next_idx = file.offsets[rand:rand+2]
    # -3 removes \n%\n
    cookie = file.data[idx:next_idx-3]
    # Replace tabs for spaces
    cookie = cookie.expandtabs(8)
    # Decode text
    cookie = cookie.decode("utf-8")
    # Deal with rot-13
    if file.rotated:
        cookie = codecs.decode(cookie, "rot_13")
    return cookie


@api.command(auto_help=False)
async def fortune(_, client: api.Client = None) -> None:
    cookie = get_fortune()
    for line in cookie.split("\n"):
        if line:
            client.message(line)


@api.command(auto_help=False)
async def book(_, client: api.Client = None) -> None:
    cookie = get_fortune_from_file(
        next(f for f in fortunes if f.name == "literature")
    )
    for line in cookie.split("\n"):
        client.message(line)
