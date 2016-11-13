from django.contrib.auth.models import User
from mptt.models import MPTTModel
from reversion import revisions
from reversion.models import Version

from judge.models.choices import TIMEZONE, ACE_THEMES, MATH_ENGINES_CHOICES, EFFECTIVE_MATH_ENGINES
from judge.models.comment import Comment, CommentVote
from judge.models.contest import Contest, ContestTag, ContestParticipation, ContestProblem, ContestSubmission, Rating
from judge.models.interface import MiscConfig, validate_regex, NavigationBar, BlogPost, Solution
from judge.models.message import PrivateMessage, PrivateMessageThread
from judge.models.problem import ProblemGroup, ProblemType, Problem, ProblemTranslation, TranslatedProblemQuerySet, \
    TranslatedProblemForeignKeyQuerySet, License, LanguageLimit
from judge.models.problem_data import problem_data_storage, problem_directory_file, ProblemData, ProblemTestCase, \
    CHECKERS
from judge.models.profile import Profile, Organization, OrganizationRequest
from judge.models.runtime import Language, RuntimeVersion, Judge
from judge.models.submission import SUBMISSION_RESULT, Submission, SubmissionTestCase

revisions.register(Profile, exclude=['points', 'last_access', 'ip', 'rating'])
revisions.register(Problem, follow=['language_limits'])
revisions.register(LanguageLimit)
revisions.register(Contest, follow=['contest_problems'])
revisions.register(ContestProblem)
revisions.register(Organization)
revisions.register(BlogPost)
revisions.register(Solution)
revisions.register(Judge, fields=['name', 'created', 'auth_key', 'description'])
revisions.register(Language)
revisions.register(Comment, fields=['author', 'time', 'page', 'score', 'title', 'body', 'hidden', 'parent'])
