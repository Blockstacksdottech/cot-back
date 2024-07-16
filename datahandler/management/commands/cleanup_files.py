import os
from django.core.management.base import BaseCommand
from django.conf import settings
from datahandler.models import PdfFiles, UserImage


class Command(BaseCommand):
    help = 'Clean up unnecessary files from the media directories'

    def handle(self, *args, **kwargs):
        self.cleanup_pdf_files()
        self.cleanup_profile_pictures()

    def cleanup_pdf_files(self):
        media_root = settings.MEDIA_ROOT
        pdfs_directory = os.path.join(media_root, 'pdfs')
        existing_files = PdfFiles.objects.values_list('file', flat=True)

        self.cleanup_directory(pdfs_directory, existing_files)

    def cleanup_profile_pictures(self):
        media_root = settings.MEDIA_ROOT
        profile_pictures_directory = os.path.join(
            media_root, 'profile_pictures')
        existing_files = UserImage.objects.values_list(
            'profile_picture', flat=True)

        self.cleanup_directory(profile_pictures_directory, existing_files)

    def cleanup_directory(self, directory, existing_files):
        if not os.path.exists(directory):
            self.stdout.write(self.style.WARNING(
                f'Directory does not exist: {directory}'))
            return

        all_files = set(os.listdir(directory))
        existing_files_set = set(os.path.basename(f)
                                 for f in existing_files if f)

        files_to_delete = all_files - existing_files_set

        for file_name in files_to_delete:
            file_path = os.path.join(directory, file_name)
            try:
                os.remove(file_path)
                self.stdout.write(self.style.SUCCESS(f'Removed: {file_path}'))
            except OSError as e:
                self.stdout.write(self.style.ERROR(
                    f'Error removing {file_path}: {e}'))
