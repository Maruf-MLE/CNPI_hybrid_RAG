"""
Auto-generated Django models from Neon PostgreSQL database.
Generated using: python manage.py inspectdb
"""

from django.db import models


class Buildings(models.Model):
    building_id = models.AutoField(primary_key=True)
    building_code = models.CharField(unique=True, max_length=10)
    building_name_bn = models.TextField()
    direction = models.CharField(max_length=20, blank=True, null=True)
    total_floors = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'buildings'
        verbose_name = 'Building'
        verbose_name_plural = 'Buildings'

    def __str__(self):
        return f"{self.building_code} - {self.building_name_bn}"


class Institutions(models.Model):
    institution_id = models.AutoField(primary_key=True)
    name_bn = models.TextField()
    short_name = models.CharField(unique=True, max_length=20)
    board_name_bn = models.TextField(blank=True, null=True)
    total_students = models.IntegerField(blank=True, null=True)
    total_teachers = models.IntegerField(blank=True, null=True)
    total_staff = models.IntegerField(blank=True, null=True)
    total_workforce = models.IntegerField(blank=True, null=True)
    total_departments = models.IntegerField(blank=True, null=True)
    total_shifts = models.IntegerField(blank=True, null=True)
    total_labs = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'institutions'
        verbose_name = 'Institution'
        verbose_name_plural = 'Institutions'

    def __str__(self):
        return f"{self.short_name} - {self.name_bn}"


class Departments(models.Model):
    department_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    name_en = models.CharField(max_length=150)
    name_bn = models.TextField(blank=True, null=True)
    short_code = models.CharField(unique=True, max_length=20)
    shift_info = models.CharField(max_length=60, blank=True, null=True)
    total_teachers = models.IntegerField(blank=True, null=True)
    total_labs = models.IntegerField(blank=True, null=True)
    description_bn = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.short_code} - {self.name_en}"


class Designations(models.Model):
    designation_id = models.AutoField(primary_key=True)
    title_bn = models.TextField(unique=True)
    title_en = models.CharField(max_length=150, blank=True, null=True)
    category = models.CharField(max_length=40)
    rank_level = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'designations'
        verbose_name = 'Designation'
        verbose_name_plural = 'Designations'

    def __str__(self):
        return self.title_bn


class People(models.Model):
    person_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    name_bn = models.TextField()
    name_en = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=1, blank=True, null=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING, blank=True, null=True)
    designation = models.ForeignKey(Designations, models.DO_NOTHING, blank=True, null=True)
    employment_type = models.CharField(max_length=20)
    shift = models.CharField(max_length=10, blank=True, null=True)
    is_principal = models.BooleanField()
    is_vice_principal = models.BooleanField()
    is_chief_instructor = models.BooleanField()
    is_workshop_super = models.BooleanField()
    phone_primary = models.CharField(max_length=50, blank=True, null=True)
    phone_secondary = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    responsibilities_bn = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'people'
        verbose_name = 'Person'
        verbose_name_plural = 'People'

    def __str__(self):
        return self.name_bn


class Documents(models.Model):
    doc_id = models.AutoField(primary_key=True)
    chunk_id = models.CharField(unique=True, max_length=200)
    content = models.TextField()
    doc_type = models.CharField(max_length=100)
    topic = models.CharField(max_length=500, blank=True, null=True)
    department = models.CharField(max_length=20, blank=True, null=True)
    tsv = models.TextField(blank=True, null=True)  # This field type is a guess.
    meta = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    source_file = models.CharField(max_length=200, blank=True, null=True)
    embedding = models.TextField(blank=True, null=True)  # This field type is a guess.
    temporal_analysis = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'documents'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f"{self.doc_type} - {self.chunk_id[:30]}"


class Subjects(models.Model):
    subject_id = models.AutoField(primary_key=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING, blank=True, null=True)
    subject_name_en = models.CharField(max_length=200)
    subject_name_bn = models.TextField(blank=True, null=True)
    course_code = models.CharField(unique=True, max_length=20, blank=True, null=True)
    semester = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'subjects'
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __str__(self):
        return f"{self.course_code} - {self.subject_name_en}"


class Rooms(models.Model):
    room_id = models.AutoField(primary_key=True)
    building = models.ForeignKey(Buildings, models.DO_NOTHING, blank=True, null=True)
    room_number = models.CharField(unique=True, max_length=30)
    floor = models.IntegerField(blank=True, null=True)
    room_type = models.CharField(max_length=30, blank=True, null=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rooms'
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return f"{self.room_number} ({self.room_type})"


class Labs(models.Model):
    lab_id = models.AutoField(primary_key=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING, blank=True, null=True)
    lab_name_bn = models.TextField()
    lab_name_en = models.CharField(max_length=150, blank=True, null=True)
    shortcode = models.CharField(max_length=10, blank=True, null=True)
    room = models.ForeignKey(Rooms, models.DO_NOTHING, blank=True, null=True)
    description_bn = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'labs'
        verbose_name = 'Lab'
        verbose_name_plural = 'Labs'

    def __str__(self):
        return f"{self.shortcode} - {self.lab_name_bn}"


class ClassCaptains(models.Model):
    captain_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    department = models.CharField(max_length=20)
    shift = models.CharField(max_length=20)
    semester = models.IntegerField()
    captain_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=30, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    session_year = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    captain_rank = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'class_captains'
        verbose_name = 'Class Captain'
        verbose_name_plural = 'Class Captains'
        unique_together = (('institution', 'department', 'shift', 'semester', 'captain_rank'),)

    def __str__(self):
        return f"{self.captain_name} - Semester {self.semester}"


class Routines(models.Model):
    routine_id = models.AutoField(primary_key=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING)
    semester = models.CharField(max_length=30)
    session = models.CharField(max_length=20)
    group_name = models.CharField(max_length=30)
    shift = models.CharField(max_length=20, blank=True, null=True)
    class_teacher_person = models.ForeignKey(People, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'routines'
        verbose_name = 'Routine'
        verbose_name_plural = 'Routines'
        unique_together = (('department', 'semester', 'session', 'group_name'),)

    def __str__(self):
        return f"{self.department.short_code} - {self.semester} - {self.group_name}"


class RoutineClasses(models.Model):
    class_id = models.AutoField(primary_key=True)
    routine = models.ForeignKey(Routines, models.DO_NOTHING)
    day_of_week = models.CharField(max_length=15)
    period_label = models.CharField(max_length=30, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    subject = models.ForeignKey(Subjects, models.DO_NOTHING, blank=True, null=True)
    teacher_person = models.ForeignKey(People, models.DO_NOTHING, blank=True, null=True)
    room = models.ForeignKey(Rooms, models.DO_NOTHING, blank=True, null=True)
    is_free = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'routine_classes'
        verbose_name = 'Routine Class'
        verbose_name_plural = 'Routine Classes'

    def __str__(self):
        return f"{self.day_of_week} - {self.period_label}"


class ExamRoutines(models.Model):
    exam_id = models.AutoField(primary_key=True)
    department = models.ForeignKey(Departments, models.DO_NOTHING)
    semester = models.CharField(max_length=30)
    session = models.CharField(max_length=20)
    group_name = models.CharField(max_length=30, blank=True, null=True)
    subject = models.ForeignKey(Subjects, models.DO_NOTHING, blank=True, null=True)
    exam_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    room = models.ForeignKey(Rooms, models.DO_NOTHING, blank=True, null=True)
    invigilator_person = models.ForeignKey(People, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exam_routines'
        verbose_name = 'Exam Routine'
        verbose_name_plural = 'Exam Routines'

    def __str__(self):
        return f"{self.department.short_code} - {self.semester} - {self.exam_date}"


class LabAssignments(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    lab = models.ForeignKey(Labs, models.DO_NOTHING)
    person = models.ForeignKey(People, models.DO_NOTHING)
    role_in_lab = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_assignments'
        verbose_name = 'Lab Assignment'
        verbose_name_plural = 'Lab Assignments'
        unique_together = (('lab', 'person'),)

    def __str__(self):
        return f"{self.person.name_bn} - {self.lab.lab_name_bn}"


class Facilities(models.Model):
    facility_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    category = models.CharField(max_length=60, blank=True, null=True)
    title_bn = models.TextField()
    description_bn = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    recorded_year = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'facilities'
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return self.title_bn


class FuturePlans(models.Model):
    plan_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    category = models.CharField(max_length=60, blank=True, null=True)
    title_bn = models.TextField()
    description_bn = models.TextField(blank=True, null=True)
    target_year = models.CharField(max_length=20, blank=True, null=True)
    target_quantity = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'future_plans'
        verbose_name = 'Future Plan'
        verbose_name_plural = 'Future Plans'

    def __str__(self):
        return f"{self.title_bn} ({self.target_year})"


class Notices(models.Model):
    notice_id = models.AutoField(primary_key=True)
    institution = models.ForeignKey(Institutions, models.DO_NOTHING)
    category = models.CharField(max_length=60, blank=True, null=True)
    title_bn = models.TextField()
    content_bn = models.TextField()
    faq_bn = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    temporal_analysis = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notices'
        verbose_name = 'Notice'
        verbose_name_plural = 'Notices'

    def __str__(self):
        return self.title_bn[:50]


class PriorityDocuments(models.Model):
    priority_id = models.AutoField(primary_key=True)
    document = models.ForeignKey(Documents, models.CASCADE, db_column='doc_id')
    priority_order = models.IntegerField(default=0)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'priority_documents'
        verbose_name = 'Priority Document'
        verbose_name_plural = 'Priority Documents'
        ordering = ['priority_order', '-created_at']
        unique_together = (('document',),)

    def __str__(self):
        return f"Priority #{self.priority_order} - {self.document.chunk_id[:30]}"
