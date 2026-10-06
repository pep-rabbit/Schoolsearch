import time
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True, frozen=True)
class Student:
    st_last_name: str
    st_first_name: str
    grade: int
    classroom: int
    bus: int
    t_last_name: str
    t_first_name: str


STUDENT_FIELDS = (
    "st_last_name",
    "st_first_name",
    "grade",
    "classroom",
    "bus",
    "t_last_name",
    "t_first_name",
)


class SchoolDatabase:
    def __init__(self, filename="students.txt"):
        self._students = []
        self._students_by_last_name = {}
        self._students_by_teacher_last_name = {}
        self._students_by_classroom = {}
        self._students_by_bus = {}
        self._load_data(filename)

    @property
    def students(self):
        """Повертає незмінне представлення всіх записів."""
        return tuple(self._students)

    def _rebuild_indexes(self):
        self._students_by_last_name.clear()
        self._students_by_teacher_last_name.clear()
        self._students_by_classroom.clear()
        self._students_by_bus.clear()
        for student in self._students:
            self._add_student_to_index(student)

    def _add_student_to_index(self, student):
        self._students_by_last_name.setdefault(student.st_last_name, []).append(student)
        self._students_by_teacher_last_name.setdefault(student.t_last_name, []).append(student)
        self._students_by_classroom.setdefault(student.classroom, []).append(student)
        self._students_by_bus.setdefault(student.bus, []).append(student)

    @staticmethod
    def _student_from_values(values):
        if len(values) != len(STUDENT_FIELDS):
            raise ValueError("Запис має містити 7 полів")
        return Student(
            st_last_name=str(values[0]).strip(),
            st_first_name=str(values[1]).strip(),
            grade=int(values[2]),
            classroom=int(values[3]),
            bus=int(values[4]),
            t_last_name=str(values[5]).strip(),
            t_first_name=str(values[6]).strip(),
        )

    @staticmethod
    def _student_to_dict(student):
        return {field: getattr(student, field) for field in STUDENT_FIELDS}

    def _load_data(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Файл {filename} недоступний")

        suffix = Path(filename).suffix.lower()
        with open(filename, "r", encoding="utf-8", newline="") as file:
            if suffix == ".json":
                data = json.load(file)
                rows = ([item[field] for field in STUDENT_FIELDS] for item in data)
            elif suffix == ".csv":
                rows = csv.reader(file)
                next(rows, None)
            else:
                rows = (line.strip().split(",") for line in file if line.strip())

            for row in rows:
                try:
                    self._students.append(self._student_from_values(row))
                except (TypeError, ValueError, KeyError):
                    continue
        self._rebuild_indexes()

    def add_student(self, student):
        """Створює запис і повертає доданого учня."""
        if not isinstance(student, Student):
            raise TypeError("Очікується об'єкт Student")
        self._students.append(student)
        self._add_student_to_index(student)
        return student

    def get_student(self, lastname, firstname):
        """Отримує записи за ім'ям і прізвищем учня."""
        return tuple(
            student for student in self._students_by_last_name.get(lastname, ())
            if student.st_first_name == firstname
        )

    def update_student(self, old_student, **changes):
        """Оновлює запис, зберігаючи узгодженість індексів."""
        if old_student not in self._students:
            raise ValueError("Учня не знайдено")
        unknown = set(changes) - set(STUDENT_FIELDS)
        if unknown:
            raise ValueError(f"Невідомі поля: {', '.join(sorted(unknown))}")
        updated = Student(**{
            field: changes.get(field, getattr(old_student, field))
            for field in STUDENT_FIELDS
        })
        self._students[self._students.index(old_student)] = updated
        self._rebuild_indexes()
        return updated

    def update_students(self, students, **changes):
        """Оновлює всі записи, що відповідають імені та прізвищу."""
        selected = set(students)
        if not selected:
            raise ValueError("Учня не знайдено")
        unknown = set(changes) - set(STUDENT_FIELDS)
        if unknown:
            raise ValueError(f"Невідомі поля: {', '.join(sorted(unknown))}")
        self._students = [
            Student(**{
                field: changes.get(field, getattr(student, field))
                for field in STUDENT_FIELDS
            })
            if student in selected else student
            for student in self._students
        ]
        self._rebuild_indexes()

    def delete_student(self, student):
        """Видаляє запис і повертає True, якщо його знайдено."""
        try:
            self._students.remove(student)
        except ValueError:
            return False
        self._rebuild_indexes()
        return True

    def delete_students(self, students):
        """Видаляє набір записів і перебудовує індекси один раз."""
        selected = set(students)
        if not selected:
            return 0
        old_count = len(self._students)
        self._students = [
            student for student in self._students if student not in selected
        ]
        self._rebuild_indexes()
        return old_count - len(self._students)

    def save(self, filename, file_format=None):
        """Зберігає базу у форматі TXT, CSV або JSON."""
        file_format = (file_format or Path(filename).suffix.lstrip(".")).lower()
        extensions = {"txt": ".txt", "csv": ".csv", "json": ".json"}
        if file_format not in extensions:
            raise ValueError("Підтримуються формати: txt, csv і json")
        if not Path(filename).suffix:
            filename += extensions[file_format]

        temporary_name = f"{filename}.tmp"
        try:
            with open(temporary_name, "w", encoding="utf-8", newline="") as file:
                if file_format == "json":
                    json.dump(
                        [self._student_to_dict(student) for student in self._students],
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )
                elif file_format == "csv":
                    writer = csv.DictWriter(file, fieldnames=STUDENT_FIELDS)
                    writer.writeheader()
                    writer.writerows(self._student_to_dict(student) for student in self._students)
                else:
                    writer = csv.writer(file)
                    writer.writerows(
                        (getattr(student, field) for field in STUDENT_FIELDS)
                        for student in self._students
                    )
            os.replace(temporary_name, filename)
        except Exception:
            if os.path.exists(temporary_name):
                os.remove(temporary_name)
            raise


    def search_by_student_last_name(self, lastname):
        return self._students_by_last_name.get(lastname, [])

    def search_by_teacher_last_name(self, lastname):
        return self._students_by_teacher_last_name.get(lastname, [])

    def search_by_classroom(self, classroom_num):
        return self._students_by_classroom.get(classroom_num, [])

    def search_by_bus(self, bus_num):
        return self._students_by_bus.get(bus_num, [])

    def info(self):
        return {
            "students": len(self._students),
            "teachers": len(self._students_by_teacher_last_name),
            "classrooms": len(self._students_by_classroom),
            "buses": len(self._students_by_bus),
        }


class CommandLineInterface:
    def __init__(self, database):
        self.db = database

    def run(self):
        while True:
            try:
                cmd_line = input("Введіть команду > ").strip()
            except EOFError:
                break
                
            if not cmd_line:
                continue
                
            cmd_parts = cmd_line.replace(':', ' ').split()
            if not cmd_parts:
                continue
                
            cmd = cmd_parts[0]
            
            if cmd in ("CLEAR", "Clear"):
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if cmd in ('Q', 'Quit'):
                break
                
            try:
                self._process_command(cmd, cmd_parts)
            except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
                print(f"Помилка: {error}")

    def _process_command(self, cmd, cmd_parts):
        database_time = 0.0
        is_valid_command = False
        
        # S[tudent]: <прізвище> [B[us]]
        if cmd in ('S', 'Student') and len(cmd_parts) >= 2 and not (
            cmd == "S" and len(cmd_parts) == 3 and cmd_parts[1].lower() in {"txt", "csv", "json"}
        ):
            is_valid_command = True
            lastname = cmd_parts[1]
            is_bus = len(cmd_parts) >= 3 and cmd_parts[2] in ('B', 'Bus')
            
            start_time = time.perf_counter()
            results = self.db.search_by_student_last_name(lastname)
            database_time = time.perf_counter() - start_time
            
            for s in results:
                if is_bus:
                    print(f"{s.st_last_name}, {s.st_first_name}, {s.bus}")
                else:
                    print(f"{s.st_last_name}, {s.st_first_name}, {s.grade}, {s.classroom}, {s.t_last_name}, {s.t_first_name}")
                    
        # T[eacher]: <прізвище>
        elif cmd in ('T', 'Teacher') and len(cmd_parts) >= 2:
            is_valid_command = True
            lastname = cmd_parts[1]
            
            start_time = time.perf_counter()
            results = self.db.search_by_teacher_last_name(lastname)
            database_time = time.perf_counter() - start_time
            
            for s in results:
                print(f"{s.st_last_name}, {s.st_first_name}")
                
        # C[lassroom]: <номер>
        elif cmd in ('C', 'Classroom') and len(cmd_parts) >= 2:
            try:
                class_num = int(cmd_parts[1])
                is_valid_command = True
                
                start_time = time.perf_counter()
                results = self.db.search_by_classroom(class_num)
                database_time = time.perf_counter() - start_time
                
                for s in results:
                    print(f"{s.st_last_name}, {s.st_first_name}")
            except ValueError:
                return
                
        # B[us]: <номер>
        elif cmd in ('B', 'Bus') and len(cmd_parts) >= 2:
            try:
                bus_num = int(cmd_parts[1])
                is_valid_command = True
                
                start_time = time.perf_counter()
                results = self.db.search_by_bus(bus_num)
                database_time = time.perf_counter() - start_time
                
                for s in results:
                    print(f"{s.st_last_name}, {s.st_first_name}, {s.grade}, {s.classroom}")
            except ValueError:
                return

        # A[dd]: <прізвище> <ім'я> <клас> <кабінет> <автобус>
        #       <прізвище_вчителя> <ім'я_вчителя>
        elif cmd in ("A", "Add") and len(cmd_parts) == 8:
            student = self.db._student_from_values(cmd_parts[1:])
            start_time = time.perf_counter()
            self.db.add_student(student)
            database_time = time.perf_counter() - start_time
            is_valid_command = True
            print("Запис додано.")

        # D[elete]: <прізвище> <ім'я>
        elif cmd in ("D", "Delete") and len(cmd_parts) >= 3:
            start_time = time.perf_counter()
            matches = self.db.get_student(cmd_parts[1], cmd_parts[2])
            if not matches:
                raise ValueError("Учня не знайдено")
            deleted_count = self.db.delete_students(matches)
            database_time = time.perf_counter() - start_time
            is_valid_command = True
            print(f"Видалено записів: {deleted_count}.")

        # U[pdate]: <прізвище> <ім'я> <поле> <нове_значення>
        elif cmd in ("U", "Update") and len(cmd_parts) == 5:
            field = cmd_parts[3]
            if field not in STUDENT_FIELDS:
                raise ValueError(f"Невідоме поле: {field}")

            start_time = time.perf_counter()
            matches = self.db.get_student(cmd_parts[1], cmd_parts[2])
            if not matches:
                raise ValueError("Учня не знайдено")
            lookup_time = time.perf_counter() - start_time
            old_value = getattr(matches[0], field)
            new_value = type(old_value)(cmd_parts[4])
            start_time = time.perf_counter()
            self.db.update_students(matches, **{field: new_value})
            database_time = lookup_time + time.perf_counter() - start_time
            is_valid_command = True
            print(f"Оновлено записів: {len(matches)}.")

        # S[ave]: <формат> <назва_файлу>
        elif cmd in ("S", "Save") and len(cmd_parts) == 3:
            start_time = time.perf_counter()
            self.db.save(cmd_parts[2], cmd_parts[1])
            database_time = time.perf_counter() - start_time
            is_valid_command = True
            print(f"Дані збережено у {cmd_parts[2]}.")

        # I[nfo]
        elif cmd in ("I", "Info") and len(cmd_parts) == 1:
            start_time = time.perf_counter()
            database_info = self.db.info()
            database_time = time.perf_counter() - start_time
            labels = {
                "students": "Учнів",
                "teachers": "Учителів",
                "classrooms": "Класів",
                "buses": "Автобусів",
            }
            for name, value in database_info.items():
                print(f"{labels[name]}: {value}")
            is_valid_command = True

        elif cmd in ("List", "Read"):
            start_time = time.perf_counter()
            students = self.db.students
            database_time = time.perf_counter() - start_time
            for student in students:
                print(", ".join(str(getattr(student, field)) for field in STUDENT_FIELDS))
            is_valid_command = True

        if is_valid_command:
            print(f"Час роботи БД: {database_time:.6f} секунд")


if __name__ == "__main__":
    try:
        db = SchoolDatabase()
        CommandLineInterface(db).run()
    except (FileNotFoundError, OSError, json.JSONDecodeError) as error:
        print(f"Помилка завантаження бази: {error}")