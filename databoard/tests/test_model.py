import os

import databoard.config as config
from numpy.testing import assert_array_equal
from databoard import db
from databoard.model import NameClashError, MergeTeamError,\
    Team, Submission, CVFold, User
import databoard.db_tools as db_tools


from databoard.remove_test_db import recreate_test_db


def test_set_config_to_test():
    config.min_duration_between_submissions = 0
    config.config_object.ramp_name = 'iris'
    origin_path = os.path.join('ramps', config.config_object.ramp_name)
    config.root_path = os.path.join('.')
    tests_path = os.path.join('databoard', 'tests')

    config.raw_data_path = os.path.join(origin_path, 'data', 'raw')
    config.public_data_path = os.path.join(tests_path, 'data', 'public')
    config.private_data_path = os.path.join(tests_path, 'data', 'private')
    config.submissions_d_name = 'test_submissions'
    config.submissions_path = os.path.join(
        config.root_path, config.submissions_d_name)
    config.deposited_submissions_path = os.path.join(
        origin_path, config.deposited_submissions_d_name)
    config.sandbox_path = os.path.join(
        origin_path, config.sandbox_d_name)
    config.config_object.n_cpus = 3


def test_recreate_test_db():
    recreate_test_db()


def test_password_hashing():
    plain_text_password = "hjst3789ep;ocikaqjw"
    hashed_password = db_tools.get_hashed_password(plain_text_password)
    assert db_tools.check_password(plain_text_password, hashed_password)
    assert not db_tools.check_password("hjst3789ep;ocikaqji", hashed_password)


def test_setup_problem():
    file_types = [
        {'name': 'classifier.py', 'type': 'python', 'is_editable': True,
         'max_size': None},
    ]
    db_tools.setup_problem(file_types)
    # to check what happens when files are already there
    db_tools.setup_problem(file_types)


def test_add_cv_folds():
    specific = config.config_object.specific
    specific.prepare_data()
    _, y_train = specific.get_train_data()
    cv = specific.get_cv(y_train)
    db_tools.add_cv_folds(cv)
    cv_folds = db.session.query(CVFold)
    for cv_fold_1, cv_fold_2 in zip(cv, cv_folds):
        train_is, test_is = cv_fold_1
        # print cv_fold_1
        # print cv_fold_2
        assert_array_equal(train_is, cv_fold_2.train_is)
        assert_array_equal(test_is, cv_fold_2.test_is)


def test_create_user():
    # db_tools.add_users_from_file('databoard/tests/data/users_to_add.csv')
    db_tools.create_user(
        name='kegl', password='wine fulcra kook homy', lastname='Kegl',
        firstname='Balazs', email='balazs.kegl@gmail.com',
        access_level='admin')
    db_tools.create_user(
        name='agramfort', password='bla', lastname='Gramfort',
        firstname='Alexandre', email='alexandre.gramfort@gmail.com',
        access_level='admin')
    db_tools.create_user(
        name='akazakci', password='bla', lastname='Akin',
        firstname='Kazakci', email='osmanakin@gmail.com',
        access_level='user')
    db_tools.create_user(
        name='mcherti', password='bla', lastname='Cherti',
        firstname='Mehdi', email='mehdicherti@gmail.com',
        access_level='admin')
    db_tools.create_user(
        name='djabbz', password='bla', lastname='Benbouzid',
        firstname='Djalel', email='djalel.benbouzid@gmail.com',
        access_level='user')

    try:
        db_tools.create_user(
            name='kegl', password='bla', lastname='Kegl',
            firstname='Balazs', email='balazs.kegl@hotmail.com')
    except NameClashError as e:
        assert e.value == 'username is already in use'

    try:
        db_tools.create_user(
            name='kegl_dupl_email', password='bla', lastname='Kegl',
            firstname='Balazs', email='balazs.kegl@gmail.com')
    except NameClashError as e:
        assert e.value == 'email is already in use'


def test_merge_teams():
    db_tools.merge_teams(
        name='kemfort', initiator_name='kegl', acceptor_name='agramfort')
    db_tools.merge_teams(
        name='mchezakci', initiator_name='mcherti', acceptor_name='akazakci')
    try:
        db_tools.merge_teams(
            name='kemfezakci', initiator_name='kemfort',
            acceptor_name='mchezakci')
    except MergeTeamError as e:
        assert e.value == \
            'Too big team: new team would be of size 4, the max is 3'

    try:
        db_tools.merge_teams(
            name='kezakci', initiator_name='kegl', acceptor_name='mchezakci')
    except MergeTeamError as e:
        assert e.value == 'Merge initiator is not active'
    try:
        db_tools.merge_teams(
            name='mchezagl', initiator_name='mchezakci', acceptor_name='kegl')
    except MergeTeamError as e:
        assert e.value == 'Merge acceptor is not active'

    # simulating that in a new ramp single-user teams are active again, so
    # they can try to re-form eisting teams
    Team.query.filter_by(name='akazakci').one().is_active = True
    Team.query.filter_by(name='mcherti').one().is_active = True
    db.session.commit()
    try:
        db_tools.merge_teams(
            name='akazarti', initiator_name='akazakci',
            acceptor_name='mcherti')
    except MergeTeamError as e:
        assert e.value == \
            'Team exists with the same members, team name = mchezakci'
    # but it should go through if name is the same (even if initiator and
    # acceptor are not the same)
    db_tools.merge_teams(
        name='mchezakci', initiator_name='akazakci', acceptor_name='mcherti')

    Team.query.filter_by(name='akazakci').one().is_active = False
    Team.query.filter_by(name='mcherti').one().is_active = False
    db.session.commit()


def test_make_submission():
    db_tools.make_submission('kemfort', 'rf')
    db_tools.make_submission('mchezakci', 'rf')
    db_tools.make_submission('kemfort', 'rf2')
    db_tools.make_submission('kemfort', 'training_error')
    db_tools.make_submission('kemfort', 'validating_error')
    db_tools.print_submissions()

    # resubmitting 'new' is OK
    db_tools.make_submission('kemfort', 'rf')

    team = Team.query.filter_by(name='kemfort').one()
    submission = Submission.query.filter_by(team=team, name='rf').one()

    submission.state = 'training_error'
    db.session.commit()
    # resubmitting 'error' is OK
    db_tools.make_submission('kemfort', 'rf')

    submission.state = 'testing_error'
    db.session.commit()
    # resubmitting 'error' is OK
    db_tools.make_submission('kemfort', 'rf')

    submission.state = 'trained'
    db.session.commit()
    # resubmitting 'trained' is not OK
    try:
        db_tools.make_submission('kemfort', 'rf')
    except db_tools.DuplicateSubmissionError as e:
        assert e.value == 'Submission "rf" of team "kemfort" exists already'

    submission.state = 'testing_error'
    db.session.commit()
    # submitting non-existing file
    # try:
    #     db_tools.make_submission_and_copy_files(
    #         'kemfort', 'rf', 'test_submissions/kemfort/' +
    #         'm3af2c986ca68d1598e93f653c0c0ae4b5e3449ae')
    # except MissingSubmissionFileError as e:
    #     assert e.value == 'kemfort/rf/feature_extractor.py: ' +\
    #         './test_submissions/kemfort/' +\
    #         'm3af2c986ca68d1598e93f653c0c0ae4b5e3449ae/feature_extractor.py'


# TODO: test all kinds of error states
def train_test_submissions():
    config.is_parallelize = False
    db_tools.train_test_submissions()
    db_tools.train_test_submissions()
    db_tools.train_test_submissions(force_retrain_test=True)
    config.is_parallelize = True
    db_tools.train_test_submissions(force_retrain_test=True)


def test_compute_contributivity():
    db_tools.compute_contributivity()


def test_print_db():
    print '\n'
    db_tools.print_users()
    print '\n'
    db_tools.print_active_teams()
    print '\n'
    db_tools.print_submissions()


def test_leaderboard():
    print '\n'
    print('***************** Leaderboard ****************')
    print db_tools.get_public_leaderboard()
    print('*********** Leaderboard of kemfort ***********')
    print db_tools.get_public_leaderboard(team_name='kemfort')
    print('*********** Leaderboard of kegl ***********')
    print db_tools.get_public_leaderboard(
        user=User.query.filter_by(name='kegl').one())
    print('*********** Failing submissions of kegl ***********')
    print db_tools.get_failed_submissions(
        user=User.query.filter_by(name='kegl').one())
