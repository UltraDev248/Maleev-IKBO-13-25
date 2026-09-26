## Задание 1

~$ grep -o '^[^:]\*' /etc/passwd | sort

## Задание 2

~$ grep -v '^#' /etc/protocols | awk 'NF>=2 {print $2, $1}' | sort -nr | head -n 5

## Задание 3

~$ nano task3.sh

#!/usr/bin/env bash

text="$1"
len=${#text}

border=$(printf '%*s' "$((len + 2))" '' | tr ' ' '-')

echo "+${border}+"
echo "| ${text} |"
echo "+${border}+"

~$ chmod +x task3.sh
~$ ./task3.sh "Hello from RTU MIREA!"

## Задание 4

~$ nano task4.sh

#!/usr/bin/env bash

if [[-z "$1" || ! -f "$1"]]; then
echo "Использование: $0 <файл>" >&2
exit 1
fi

grep -oE '[a-zA-Z\_][a-zA-Z0-9_]\*' "$1" | sort -u | xargs

~$ nano hello.c

#include <stdio.h>

void main() {
printf("hello world\n");
return;
}

~$ chmod +x task4.sh
~$ ./task4.sh hello.c

## Задание 5

~$ nano task5.sh

#!/usr/bin/env bash

if [[-z "$1" || ! -f "$1"]]; then
echo "Использование: $0 <файл_команды>" >&2
exit 1
fi

target="$1"

chmod +x "$target" && sudo cp "$target" /usr/local/bin/

~$ chmod +x task5.sh
~$ ./task5.sh task3.sh
~$ task3.sh "Hello from RTU MIREA!"

## Задание 6

~$ nano task6.sh

#!/usr/bin/env bash

for file in \*.{c,js,py}; do
[[-f "$file"]] || continue

    first_line=$(head -n 1 "$file")
    case "$file" in
        *.c|*.js)
            if [[ "$first_line" =~ ^[[:space:]]*(//|/\*) ]]; then
                echo "$file: Есть комментарий"
            else
                echo "$file: Нет комментария"
            fi
            ;;
        *.py)
            if [[ "$first_line" =~ ^[[:space:]]*# ]]; then
                echo "$file: Есть комментарий"
            else
                echo "$file: Нет комментария"
            fi
            ;;
    esac

done

~$ echo "// комментарий" > test1.c
~$ echo "int main() {}" > test2.c
~$ echo "# комментарий" > test3.py
~$ echo "print('Hello')" > test4.py
~$ echo "/_ Многострочный комментарий _/" > test5.js
~$ chmod +x task6.sh
~$ ./task6.sh

## Задание 7

~$ nano task7.sh

#!/usr/bin/env bash

dir="${1:-.}"

find "$dir" -type f -exec md5sum {} + | sort | awk '{
hash = $1
$1 = ""
file = substr($0, 2)
count[hash]++
files[hash] = files[hash] "\n " file
}
END {
for (h in count) {
if (count[h] > 1) {
print "Группа дубликатов (хэш " h "):" files[h] "\n"
}
}
}'

~$ mkdir -p task7/subfolder
~$ echo "Привет, мир!" > task7/file1.txt
~$ echo "Привет, мир!" > task7/file2.txt
~$ echo "Привет, мир!" > task7/subfolder/file3.txt
~$ echo "Другой текст" > task7/file4.txt
~$ chmod +x task7.sh
~$ ./task7.sh task7

## Задание 8

~$ nano task8.sh

#!/usr/bin/env bash

dir="$1"
ext="$2"

if [[-z "$dir" || -z "$ext"]]; then
echo "Использование: $0 <директория> <расширение>" >&2
exit 1
fi

archive="archive\_${ext}.tar"
find "$dir" -type f -name "\*.$ext" -print0 | tar -cvf "$archive" --null -T -

-$ chmod +x task8.sh
~$ mkdir -p task8/subfolder
~$ touch task8/file1.txt
~$ touch task8/file2.txt
~$ touch task8/subfolder/file3.txt
~$ ./task8.sh task8 txt

## Задание 9

~$ nano task9.sh

#!/usr/bin/env bash

infile="$1"
outfile="$2"

if [[-z "$infile" || -z "$outfile"]]; then
echo "Использование: $0 <входной*файл> <выходной*файл>" >&2
exit 1
fi

sed 's/ /\t/g' "$infile" > "$outfile"

~$ chmod +x task9.sh
-$ echo " Text with four spaces at the start" > input.txt
~$ ./task9.sh input.txt output.txt
~$ cat -T output.txt

## Задание 10

~$ nano task10.sh

#!/usr/bin/env bash

dir="${1:-.}"

if [[! -d "$dir"]]; then
echo "Ошибка: '$dir' не является директорией" >&2
exit 1
fi

find "$dir" -maxdepth 1 -type f -empty

~$ chmod +x task10.sh
~$ mkdir task10
~$ touch task10/empty1.txt
~$ touch task10/empty2.txt
~$ echo "Есть текст" > task10/not_empty.txt
~$ mkdir task10/empty_folder
~$ ./task10.sh task10
