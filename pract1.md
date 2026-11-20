## Задача 1
Вывести отсортированный в алфавитном порядке список имен пользователей в файле passwd.

Так как имена в passwd хранятся в отделённой двоеточием первой ячейке каждой из своих строк, для поиска командой grep используем регулярное выражение `^[^:]*`, которое соответствует любому набору не-двоеточий в начале строки. Также поставим флаг -o, чтобы выводило только соответствующие части строк, затем перенаправляем выход в следующую команду sort, чтобы вывести в алфавитном порядке.


```
[deam@archlinux ~]$ grep -o '^[^:]*' /etc/passwd | sort
alpm
avahi
bin
daemon
dbus
deam
flatpak
ftp
http
mail
nobody
pcscd
plasmalogin
polkitd
root
sddm
systemd-coredump
systemd-imds
systemd-journal-remote
systemd-network
systemd-oom
systemd-resolve
systemd-timesync
tss
uuidd
```

---

## Задача 2
Вывести данные /etc/protocols в отформатированном и отсортированном порядке для 5 наибольших портов.

Для форматирования используем команду awk, работующую со столбцами. Так как обозначения столбцов $1 и $2 воспринимаются консолью как названия пространственных переменных при использовании двойных кавычек, испольуем вместо них одинарные. Для отсечения пяти высших результатов используем перенаправление в head.

```
[deam@archlinux ~]$ grep -v "^#" /etc/protocols | awk '{print $2, $1}' | sort -nr | head -n 5
255 reserved
147 bit-emu
146 homa
145 nsh
144 aggfrag
```

## Задача 3

Написать программу banner средствами bash для вывода текстов с форматом баннера.

В начале вставим несколько строк хорошего тона для того, чтобы скрипт было безопасно запускать. В шебанге укажем интерпретатор из /usr/bin/env; Также зададим опции, чтобы он завершался при первой ошибке, ошибался при обращении к несуществующей переменной, и ломал конвееры команд, если хоть одна из них выдаёт ошибку.
При отсутствии аргументов будем сразу выводить подсказку по использованию в поток ошибок и выходить с кодом 1.

```
#!/usr/bin/bash
set -euo pipefail

if (($# == 0)); then
    echo "Введите текст для баннера" >&2
    exit 1
fi

text="$*"  #                                    выводимый текст есть все аргументы через пробел
width=$(( ${#text} + 2 ))  #                    длина цепочки минусов
string=$(printf '%*s' "$width" | tr " " "-")  # переменная со строкой из width минусов

printf '+%s+\n' "$string"
printf '| %s |\n' "$text"
printf '+%s+\n' "$string"
```

Теперь пропишем файлу исполняемость используя chmod +x и запустим:

```
[deam@archlinux ~]$ ./banner foobar baz quux ! 1
+---------------------+
| foobar baz quux ! 1 |
+---------------------+
```

## Задача 4
Написать программу для вывода всех идентификаторов (по правилам C/C++ или Java) в файле, без повторений.

Не считая правил хорошего тона, решение можно сделать в одну строчку при помощи конвеера grep в sort с флагом u (уникальности).

```
#!/usr/bin/bash
set -euo pipefail

if (($# == 0)); then
    echo "Введите название файла" >&2
    exit 1
fi

grep -Eo '[A-Za-z_$][A-Za-z0-9_$]*' "$1" | sort -u | paste -s -d ' '
```

Запустим:

```
[deam@archlinux ~]$ ./identificator /home/deam/Downloads/Metro.py
AccessPoint AccessPointNet acessPointNet and apn base class cost def depots dict for if __init__ int is length level lights Line maintenance maintenanceCost net None of pass platCapacity platWidth position print railConnections rails result self station Station the updateMainCost updatePlatCap walkConnections width
```

## Задача 5
Написать программу для регистрации пользовательской команды (правильные права доступа и копирование в /usr/local/bin).

При помощи команды install можно сразу же копировать и выставить правила доступа файлу через -m. Корректные флаги доступа — `(--- rwx r-x r-x)`, то есть (0 7 5 5).

```
#!/usr/bin/bash
set -euo pipefail

if (($# == 0)); then
    echo "Введите название файла" >&2
    exit 1
fi

cmd="$1"

if [[ ! -f "$cmd" ]]; then
  echo "Файл не найден" >&2
  exit 1
fi

install -m 0755 "$cmd" /usr/local/bin/
```

Так как перемещение в /usr/local/bin/ требует прав root, запускать программу надо от суперпользователя.

## Задача 6
Написать программу для проверки наличия комментария в первой строке файлов с расширением c, js и py.

```
#!/usr/bin/bash
set -euo pipefail

dir="${1:-.}"  # если нет целевой директории, используем текущую (.)

if [[ ! -d "$dir" ]]; then
  echo "Неверная директория" >&2
  exit 1
fi

while IFS= read -r -d '' file; do  # читаем до нулевого байта (''), оставляем пробельные символы на концах (IFS=)
  if [[ "$file" == *.c || "$file" == *.js ]]; then
    re='^[[:space:]]*(//|/\*)'
  elif [[ "$file" == *.py ]]; then
    re='^[[:space:]]*#'
  else
    continue
  fi

  if head -n 1 -- "$file" | grep -Eq "$re"; then
    echo "$file: есть комментарий"
  else
    echo "$file: нет комментария"
  fi
done < <(find "$dir" -type f \( -name '*.c' -o -name '*.js' -o -name '*.py' \) -print0)  # передаём список файлов директории в цикл
```

## Задача 7
Написать программу для нахождения файлов-дубликатов (имеющих 1 или более копий содержимого) по заданному пути (и подкаталогам).

```
#!/usr/bin/bash
set -euo pipefail

dir="${1:-.}"

if [[ ! -d "$dir" ]]; then
  echo "Неверная директория" >&2
  exit 1
fi

find "$dir" -type f -exec sha256sum {} + | sort | awk '
{
  hash = $1
  file = substr($0, length(hash) + 3)

  if (hash == prev) {
    if (!shown) {
      print prev_file
      shown = 1
    }
    print file
  } else {
    prev = hash
    prev_file = file
    shown = 0
  }
}'
```

## Задача 8
Написать программу, которая находит все файлы в данном каталоге с расширением, указанным в качестве аргумента и архивирует все эти файлы в архив tar.

```
#!/usr/bin/bash
set -euo pipefail

if (($# != 3)); then
  echo "Укажите директорию, расширение, и название архива" >&2
  exit 1
fi

dir="$1"
ext="$2"
archive="$3"

if [[ ! -d "$dir" ]]; then
  echo "Неверная директория" >&2
  exit 1
fi

mapfile -d '' files < <(find "$dir" -maxdepth 1 -type f -name "*.$ext" -print0)

if ((${#files[@]} == 0)); then
  echo "Не найдены файлы с расширением $ext" >&2
  exit 1
fi

tar -cf "$archive" -- "${files[@]}"
```

## Задача 9
Написать программу, которая заменяет в файле последовательности из 4 пробелов на символ табуляции. Входной и выходной файлы задаются аргументами.

```
#!/usr/bin/bash
set -euo pipefail

if (($# != 2)); then
  echo "Укажите входной и выходной файлы >&2
  exit 1
fi

sed 's/    /\t/g' "$1" > "$2"
```

## Задача 10
Написать программу, которая выводит названия всех пустых текстовых файлов в указанной директории. Директория передается в программу параметром.

```
#!/usr/bin/bash
set -euo pipefail

if (($# != 1)); then
  echo "Укажите название директории" >&2
  exit 1
fi

dir="$1"

if [[ ! -d "$dir" ]]; then
  echo "Неверная директория" >&2
  exit 1
fi

find "$dir" -maxdepth 1 -type f -empty \
  \( -name '*.txt' -o -name '*.md' -o -name '*.log' -o -name '*.c' -o -name '*.js' -o -name '*.py' \) \
  -printf '%f\n'
```
