from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datahandler.models import Article

class Command(BaseCommand):
    help = "Populates slugs for existing articles based on their titles."

    def handle(self, *args, **kwargs):
        # Iterate through all articles
        for article in Article.objects.all():
            if not article.slug:  # Only generate a slug if it's empty
                base_slug = slugify(article.title)
                slug = base_slug
                counter = 1

                # Ensure uniqueness
                while Article.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Assign the unique slug and save the article
                article.slug = slug
                article.save()

                self.stdout.write(self.style.SUCCESS(f'Updated article "{article.title}" with slug "{slug}"'))

        self.stdout.write(self.style.SUCCESS("Successfully populated slugs for all articles."))