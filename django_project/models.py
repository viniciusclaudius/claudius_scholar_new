from django.db import models
from django.contrib.auth.models import User
from django.db.models import CASCADE
from django.db.models.fields import related
from django.dispatch import receiver
from django.db.models.signals import post_save
import uuid
import stripe
from django.conf import settings
from datetime import timedelta, date, datetime

stripe.api_key = settings.GET_STRIPE_SECRET()

# Create your models here.

# ----- Input Fields ----- #
# Notes: 
# Let blank=False for required fields
# Let null=True unless a field has a default value and you have special reason

def user_directory_path_cv(instance, filename):
    return '{}/{}_{}/cv/{}'.format(settings.AWS_S3_PATH, instance.user.id, instance.user.username, filename)

def user_directory_path_bio(instance, filename):
    return '{}/{}_{}/bio/{}'.format(settings.AWS_S3_PATH, instance.user.id, instance.user.username, filename)

def user_directory_path_abstract(instance, filename):
    return '{}/{}_{}/paper_{}/abstract/{}'.format(settings.AWS_S3_PATH, instance.researcher.id, instance.researcher.username, instance.uuid, filename)

def user_directory_path_manuscript(instance, filename):
    return '{}/{}_{}/paper_{}/manuscript/{}'.format(settings.AWS_S3_PATH, instance.researcher.id, instance.researcher.username, instance.uuid, filename)

def user_directory_path_supplement(instance, filename):
    return '{}/{}_{}/paper_{}/supplement/{}'.format(settings.AWS_S3_PATH, instance.researcher.id, instance.researcher.username, instance.uuid, filename)

def default_user():
    user = User()
    user.save()
    return user.pk

class Journal(models.Model):
    user = models.OneToOneField(User, on_delete=CASCADE)
    name = models.CharField('Journal Name', blank=False, null=True, max_length=200)
    ranking = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    def get_journal_profile(self):
        publisher = Journal.objects.get(pk=self.id).user
        try:
            profile = JournalProfile.objects.get(user=publisher)
            return profile
        except: 
            return None

    def is_open(self):
        publisher = Journal.objects.get(pk=self.id).user
        try: 
            profile = JournalProfile.objects.get(user=publisher)
            if profile.status == 'O':
                return True
            else: 
                return False
        except: 
            return False


class Paper(models.Model):
    FIELDS = (
        ('A', 'Admiralty (Maritime) Law'),
        ('B', 'Bankruptcy Law'),
        ('BC', 'Business (Corporate) Law'),
        ('CP', 'Civil Procedure'),
        ('CR', 'Civil Rights Law'),
        ('CL', 'Constitutional Law'),
        ('CO', 'Contracts'),
        ('C', 'Criminal Law'),
        ('CRP', 'Criminal Procedure'),
        ('DR', 'Dispute Resolution'),
        ('E', 'Entertainment Law'),
        ('EV', 'Environment Law'),
        ('F', 'Family Law'),
        ('H', 'Health Law'),
        ('I', 'Immigration Law'),
        ('IP', 'Intellectual Property Law'),
        ('IN', 'International Law'),
        ('L', 'Labor (Employment) Law'),
        ('M', 'Military Law'),
        ('PI', 'Personal Injury Law'),
        ('P', 'Property'),
        ('RE', 'Real Estate Law'),
        ('T', 'Tax Law'),
        ('TO', 'Torts'),
    )

    RANKINGS = (
        ('-1', 'None'),
        ('14', 'T-14'),
        ('25', 'T-25'),
        ('50', 'T-50'),
        ('100', 'T-100'),
        ('101', 'T-100+')
    )

    TYPE = (
        ('A', 'Article'),
        ('E', 'Essay')
    )

    title = models.CharField('Paper title', blank=False, null=True, max_length=200)
    field_of_law = models.CharField('Field of law', blank=False, null=True, max_length=200, choices=FIELDS)
    authors = models.CharField('Authors', blank=False, null=True, max_length=200)

    significance = models.TextField('What is the significance of this article/essay?', blank=False, null=True)
    abstract = models.FileField('Abstract', upload_to=user_directory_path_abstract, null=True, blank=False)
    manuscript = models.FileField('Manuscript', upload_to=user_directory_path_manuscript, null=True, blank=False)
    supplement = models.FileField('Supplement', upload_to=user_directory_path_supplement, null=True, blank=True)
    abstract_key = models.CharField('Abstract key for AWS S3', max_length=1024, null=True, blank=True)
    manuscript_key = models.CharField('Manuscript key for AWS S3', max_length=1024, null=True, blank=True)
    supplement_key = models.CharField('Supplement key for AWS S3', max_length=1024, null=True, blank=True)
    submission_date = models.DateField('Submission date', null=True, blank=True, auto_now_add=True)
    researcher = models.ForeignKey(User, on_delete=CASCADE, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    journals = models.ManyToManyField(Journal)

    best_offer = models.CharField('Best offer', blank=False, null=True, max_length=30, choices=RANKINGS)
    paper_type = models.CharField('Submission Type', blank=True, null=True, default='A', max_length=30, choices=TYPE)

    submission_criteria_satisfied = models.BooleanField('Please confirm that you have read the submission criteria for each journal to which you are submitting and that your submission meets all relevant criteria', default=False)

class Evaluation(models.Model): 
    FIELDS_1 = (
        ('A', 'Accept'),
        ('R', 'Reject'),
    )

    FIELDS_2 = (
        ('A', 'Accept for Review'),
        ('R', 'Decline to Review'),
    )

    YESNO = (
        ('Y', 'Yes'),
        ('N', 'No'),
    )

    CHOICES = (
        (10, '10 - Outstanding'),
        (9, '9 - Excellent'),
        (8, '8 - Very good'),
        (7, '7 - Good'),
        (6, '6 - Above Average'),
        (5, '5 - Average'),
        (4, '4 - Below Average'),
        (3, '3 - Weak'),
        (2, '2 - Very Weak'),
        (1, '1 - Extremely Weak'),
    )

    STATUSES = (
        ('N', 'Not Yet Started'),
        ('UR', 'Under Review'),
        ('UFR', 'Under Full Board Review'),
        ('C', 'Complete'),
    )

    paper = models.ForeignKey(Paper, related_name="evals", on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=CASCADE)
    comments = models.TextField()
    rating = models.IntegerField('Quality of Submission (1-10)', choices=CHOICES, null=True)
    offered = models.CharField('Decision', blank=False, null=True, max_length=20, choices=FIELDS_1)
    date = models.DateTimeField(auto_now_add=True)
    offer_accepted = models.CharField('Offer Decision', blank=True, max_length=5, choices=YESNO)
    status = models.CharField('Evaluation Status', blank=False, default='N', max_length=20, choices=STATUSES)
    start_decision = models.CharField('Decision to review paper', blank=False, null=True, max_length=20, choices=FIELDS_2)
    evaluate_start = models.DateTimeField(auto_now_add=False, blank=True, null=True)
    eval_rubric = models.TextField('Rubric', blank=True, null=True)

class PersonalProfile(models.Model):
    POSITIONS = (
        ('P', 'Professor'),
        ('PD', 'Post-Doc/Fellow'),
        ('GS', 'Graduate (MA/MS/PhD) Student'),
        ('LS', 'Law Student'),
        ('U', 'Undergraduate'),
        ('PR', 'Practitioner'),
        ('J', 'Judge'),
        ('O', 'Other'),
    )
    user = models.OneToOneField(User, on_delete=CASCADE)
    first_name = models.CharField('First name', blank=False, null=True, max_length=200)
    last_name = models.CharField('Last name', blank=False, null=True, max_length=200)
    institution = models.CharField('Institution', blank=True, null=True, max_length=200)
    email = models.EmailField('Email', blank=False, null=True, max_length=200)
    current_position = models.CharField('Current Position', choices=POSITIONS, blank=True, null=True, max_length=200)
    cv = models.FileField('CV', upload_to=user_directory_path_cv, null=True, blank=True)
    bio = models.FileField('Bio', upload_to=user_directory_path_bio, null=True, blank=True)
    cv_key = models.CharField('CV key for AWS S3', max_length=1024, null=True, blank=True)
    bio_key = models.CharField('Bio key for AWS S3', max_length=1024, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)

class UserProfile(models.Model):
    TYPES = (
        ('R', 'Researcher'),
        ('P', 'Publisher'),
        ('E', 'Editor'),
    )
    user = models.OneToOneField(User, on_delete=CASCADE)
    user_type = models.CharField('Type', blank=False, null=True, choices=TYPES, max_length=200)
    stripe_id = models.CharField('Stripe ID', blank=True, null=True, max_length=200)
    billing_saved = models.BooleanField('Billing saved', blank=True, null=True, default=False)
    is_email_verified = models.BooleanField(default=False)
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

def stripeCallback(sender, request, user, **kwargs):
    user_stripe_account, created = UserProfile.objects.get_or_create(user=user)
    if created:
        print("Created Stripe Account for user: %s" % user)

    if user_stripe_account.stripe_id is None or user_stripe_account.stripe_id == '':
        new_stripe_id = stripe.Customer.create(email=user.email).id
        user_stripe_account.stripe_id = new_stripe_id['id']
        user_stripe_account.save()

class JournalProfile(models.Model):
    STATUS = (
        ('O', 'Open'),
        ('C', 'Closed'),
    )
    user = models.OneToOneField(User, on_delete=CASCADE, related_name='jprofile')
    status = models.CharField('Submission status', choices=STATUS, blank=False, null=True, max_length=10)
    email = models.EmailField('Email', blank=False, null=True, max_length=200)
    description = models.TextField('Journal description', blank=False, null=True)
    submission_criteria = models.TextField('Submission criteria', blank=True, null=True)
    rubric = models.TextField('Paper Rubric (Only visible to editors)', blank=True, null=True)

class JournalGroupEditors(models.Model):
    journal = models.ForeignKey(Journal, on_delete=CASCADE)
    editor = models.OneToOneField(User, on_delete=CASCADE, null=True)

class Message(models.Model):
    author = models.ForeignKey(User, related_name='author_messages', on_delete=CASCADE)
    content = models.TextField()
    room_name = models.TextField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def last_message(room_name):
        return Message.objects.all().filter(room_name=room_name).latest('timestamp')

    def last_messages_all(room_name):
        return reversed(Message.objects.order_by('-timestamp').all().filter(room_name=room_name))

class Contact(models.Model):
    email = models.EmailField()
    journal = models.CharField(max_length=100, default='')
    subject = models.CharField(max_length=100, default='')
    message = models.TextField()

    def __str__(self):
        return self.email
