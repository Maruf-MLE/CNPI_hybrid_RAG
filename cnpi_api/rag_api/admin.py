"""
Django Admin configuration for RAG API models.
"""

from django.contrib import admin
from .models import (
    Buildings, Institutions, Departments, Designations, People,
    Documents, Subjects, Rooms, Labs, ClassCaptains, Routines,
    RoutineClasses, ExamRoutines, LabAssignments, Facilities,
    FuturePlans, Notices, PriorityDocuments
)


@admin.register(Institutions)
class InstitutionsAdmin(admin.ModelAdmin):
    list_display = ('institution_id', 'short_name', 'name_bn', 'total_students', 'total_teachers', 'total_departments')
    search_fields = ('name_bn', 'short_name')
    list_filter = ('created_at',)


@admin.register(Departments)
class DepartmentsAdmin(admin.ModelAdmin):
    list_display = ('department_id', 'short_code', 'name_en', 'institution', 'total_teachers', 'total_labs')
    search_fields = ('name_en', 'name_bn', 'short_code')
    list_filter = ('institution',)


@admin.register(People)
class PeopleAdmin(admin.ModelAdmin):
    list_display = ('person_id', 'name_bn', 'designation', 'department', 'employment_type', 'phone_primary')
    search_fields = ('name_bn', 'name_en', 'phone_primary', 'email')
    list_filter = ('institution', 'department', 'designation', 'employment_type', 'is_principal', 'is_vice_principal')
    readonly_fields = ('created_at',)


@admin.register(Documents)
class DocumentsAdmin(admin.ModelAdmin):
    list_display = ('doc_id', 'chunk_id', 'doc_type', 'topic', 'department', 'created_at')
    search_fields = ('chunk_id', 'content', 'topic', 'doc_type')
    list_filter = ('doc_type', 'department', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Subjects)
class SubjectsAdmin(admin.ModelAdmin):
    list_display = ('subject_id', 'course_code', 'subject_name_en', 'department', 'semester')
    search_fields = ('subject_name_en', 'subject_name_bn', 'course_code')
    list_filter = ('department', 'semester')


@admin.register(Buildings)
class BuildingsAdmin(admin.ModelAdmin):
    list_display = ('building_id', 'building_code', 'building_name_bn', 'direction', 'total_floors')
    search_fields = ('building_code', 'building_name_bn')


@admin.register(Rooms)
class RoomsAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'room_number', 'building', 'floor', 'room_type', 'department')
    search_fields = ('room_number', 'notes')
    list_filter = ('building', 'room_type', 'department', 'floor')


@admin.register(Labs)
class LabsAdmin(admin.ModelAdmin):
    list_display = ('lab_id', 'shortcode', 'lab_name_bn', 'department', 'room')
    search_fields = ('lab_name_bn', 'lab_name_en', 'shortcode')
    list_filter = ('department',)


@admin.register(Designations)
class DesignationsAdmin(admin.ModelAdmin):
    list_display = ('designation_id', 'title_bn', 'title_en', 'category', 'rank_level')
    search_fields = ('title_bn', 'title_en')
    list_filter = ('category',)


@admin.register(ClassCaptains)
class ClassCaptainsAdmin(admin.ModelAdmin):
    list_display = ('captain_id', 'captain_name', 'department', 'semester', 'shift', 'phone', 'is_active')
    search_fields = ('captain_name', 'student_id', 'phone', 'email')
    list_filter = ('institution', 'department', 'shift', 'semester', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Routines)
class RoutinesAdmin(admin.ModelAdmin):
    list_display = ('routine_id', 'department', 'semester', 'session', 'group_name', 'shift')
    search_fields = ('session', 'group_name')
    list_filter = ('department', 'semester', 'shift')
    readonly_fields = ('created_at',)


@admin.register(RoutineClasses)
class RoutineClassesAdmin(admin.ModelAdmin):
    list_display = ('class_id', 'routine', 'day_of_week', 'period_label', 'start_time', 'end_time', 'subject', 'teacher_person', 'room')
    search_fields = ('day_of_week', 'period_label')
    list_filter = ('day_of_week', 'is_free', 'routine')


@admin.register(ExamRoutines)
class ExamRoutinesAdmin(admin.ModelAdmin):
    list_display = ('exam_id', 'department', 'semester', 'subject', 'exam_date', 'start_time', 'room')
    search_fields = ('session', 'group_name')
    list_filter = ('department', 'semester', 'exam_date')
    date_hierarchy = 'exam_date'
    readonly_fields = ('created_at',)


@admin.register(LabAssignments)
class LabAssignmentsAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'lab', 'person', 'role_in_lab')
    search_fields = ('role_in_lab',)
    list_filter = ('lab',)
    readonly_fields = ('created_at',)


@admin.register(Facilities)
class FacilitiesAdmin(admin.ModelAdmin):
    list_display = ('facility_id', 'title_bn', 'category', 'institution', 'quantity', 'unit', 'status', 'recorded_year')
    search_fields = ('title_bn', 'description_bn')
    list_filter = ('institution', 'category', 'status', 'recorded_year')


@admin.register(FuturePlans)
class FuturePlansAdmin(admin.ModelAdmin):
    list_display = ('plan_id', 'title_bn', 'category', 'institution', 'target_year', 'target_quantity', 'unit')
    search_fields = ('title_bn', 'description_bn')
    list_filter = ('institution', 'category', 'target_year')


@admin.register(Notices)
class NoticesAdmin(admin.ModelAdmin):
    list_display = ('notice_id', 'title_bn', 'category', 'institution', 'created_at')
    search_fields = ('title_bn', 'content_bn')
    list_filter = ('institution', 'category', 'created_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(PriorityDocuments)
class PriorityDocumentsAdmin(admin.ModelAdmin):
    list_display = ('priority_id', 'document', 'priority_order', 'is_active', 'created_at')
    search_fields = ('document__chunk_id', 'document__content', 'reason')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('priority_order', '-created_at')
