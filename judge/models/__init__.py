from reversion import revisions

from judge.models.choices import ACE_THEMES, EFFECTIVE_MATH_ENGINES, MATH_ENGINES_CHOICES, TIMEZONE
from judge.models.comment import Comment, CommentLock, CommentVote
from judge.models.contest import Contest, ContestMoss, ContestParticipation, ContestProblem, ContestSubmission, \
    ContestTag, Rating
from judge.models.interface import BlogPost, MiscConfig, NavigationBar, validate_regex
from judge.models.problem import LanguageLimit, License, Problem, ProblemClarification, ProblemGroup, \
    ProblemPointsVote, ProblemTranslation, ProblemType, Solution, SubmissionSourceAccess, \
    TranslatedProblemQuerySet
from judge.models.problem_data import CHECKERS, ProblemData, ProblemTestCase, problem_data_storage, \
    problem_directory_file
from judge.models.profile import Class, Organization, OrganizationRequest, Profile, WebAuthnCredential
from judge.models.runtime import Judge, Language, RuntimeVersion
from judge.models.submission import SUBMISSION_RESULT, Submission, SubmissionSource, SubmissionTestCase
from judge.models.ticket import Ticket, TicketMessage

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
revisions.register(Comment, fields=['author', 'time', 'page', 'score', 'body', 'hidden', 'parent'])
del revisions
