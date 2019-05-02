#encoding:utf-8
from flask import Flask,render_template,jsonify,make_response,request,redirect,jsonify,session,escape,url_for
from flask_sqlalchemy import SQLAlchemy
import uuid,os,hashlib

class Config:
	basedir = os.path.abspath(os.path.dirname(__file__))
	SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
	SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

app = Flask(__name__)
app.secret_key = 'KALE1D0<3DAHLIA'
app.debug = False
app.config.from_object(Config)
db = SQLAlchemy(app)

class Puzzle(db.Model):
	id = db.Column(db.Integer, primary_key=True, nullable=False)
	name = db.Column(db.String(255), index=True, unique=False, nullable=False)
	unlock_score = db.Column(db.Integer, index=False, unique=False, nullable=False)
	score = db.Column(db.Integer, index=False, unique=False, nullable=False)
	tried_num = db.Column(db.Integer, index=False, unique=False, nullable=False)
	passed_num = db.Column(db.Integer, index=False, unique=False, nullable=False)
	tags = db.Column(db.String(255), index=True, unique=False, nullable=True)
	author = db.Column(db.String(255), index=True, unique=False, nullable=True)
	special_judge = db.Column(db.String(255), index=False, unique=False, nullable=True)
	answer = db.Column(db.String(255), index=False, unique=False, nullable=False)
	custom_submit = db.Column(db.Boolean(), index=False, unique=False, nullable=False)
	custom_title = db.Column(db.Boolean(), index=False, unique=False, nullable=False)
	hint = db.Column(db.String(255), index=False, unique=False, nullable=True)

	def getRating(self):
		marks = Mark.query.filter_by(puzzle=self.id).all()
		marks = list(map(lambda x: x.value, marks))
		return '{:.1f}'.format(float(sum(marks)) / (1 if (len(marks) == 0) else len(marks)))

	def getPassRate(self):
		return '{:.1%}'.format(float(self.passed_num) / (1 if int(self.tried_num) == 0 else int(self.tried_num)))

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	nickname = db.Column(db.String(64), index=True, unique=False)
	email = db.Column(db.String(64), index=True, unique=True)
	password_hash = db.Column(db.String(128), index=False, unique=False)

	def verifyPassword(self, word):
		return hashlib.md5(word).hexdigest() == self.password_hash

	def getData(self):
		data = {}
		data['email'] = self.email
		data['nickname'] = self.nickname
		data['credit'] = self.getCredit()
		data['passed'] = self.getPassedPuzzles()
		data['rank'] = self.getRank()
		data['progress'] = '{:.0%}'.format(float(len(self.getPassedPuzzles())) / (1 if len(Puzzle.query.all()) == 0 else len(Puzzle.query.all()) - 1))
		return data

	def getCredit(self):
		passed = self.getPassedPuzzles()
		credit = 0
		for puzzle in passed:
			hint = Hint.query.filter_by(user=self.id,puzzle=puzzle).first()
			if (hint != None):
				credit = credit + (Puzzle.query.get(puzzle).score / 2)
			else:
				credit = credit + Puzzle.query.get(puzzle).score
		return credit

	def getPassedPuzzles(self):
		puzzles = Puzzle.query.all()
		passed = []
		for puzzle in puzzles:
			submission = Submission.query.filter_by(user=self.id,puzzle=puzzle.id,accepted=True).first()
			if (submission != None):
				passed.append(puzzle.id)
		return passed

	def getRank(self):
		users = User.query.all()
		users.sort(key=lambda user: user.getCredit())
		users.reverse()
		return users.index(self) + 1

class Submission(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user = db.Column(db.Integer, db.ForeignKey('user.id'), unique=False, nullable=False)
	puzzle = db.Column(db.Integer, db.ForeignKey('puzzle.id'), unique=False, nullable=False)
	accepted = db.Column(db.Boolean, index=False, unique=False, nullable=False)

class Mark(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user = db.Column(db.Integer, db.ForeignKey('user.id'), unique=False, nullable=False)
	puzzle = db.Column(db.Integer, db.ForeignKey('puzzle.id'), unique=False, nullable=False)
	value = db.Column(db.Integer, index=False, unique=False, nullable=False)

class Hint(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user = db.Column(db.Integer, db.ForeignKey('user.id'), unique=False, nullable=False)
	puzzle = db.Column(db.Integer, db.ForeignKey('puzzle.id'), unique=False, nullable=False)

@app.route('/', methods=['GET'])
def page_index():
	puzzles = Puzzle.query.all()
	if ('user' in session):
		user = User.query.filter_by(email=session['user']['email']).first()
		if (user == None):
			redirect(url_for('logout'))
		session['user'] = user.getData()
		users = User.query.all()
		users.sort(key=lambda user: user.getCredit())
		users.reverse()
		users = filter(lambda x:x.nickname != 'Anonymous', users)
		top10 = []
		for user in users[:max(10,len(users))]:
			top10.append({'nickname':user.nickname,'email':user.email,'credit':user.getCredit()})
		page = render_template('index.html',user=session['user'],puzzles=puzzles,top10=top10)
	else:
		page = render_template('entry.html')
	response = make_response(page, 200)
	return response

@app.route('/puzzle/<id>', methods=['GET'])
def page_puzzle(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=session['user']['email']).first()
	puzzle = Puzzle.query.get(int(id))
	if (user.getCredit() < puzzle.unlock_score):
		return redirect(url_for('page_index'))
	else:
		return render_template('puzzle.html',puzzle=puzzle)

@app.route('/puzzle/<id>/submit', methods=['POST'])
def judge(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=session['user']['email']).first()
	puzzle = Puzzle.query.get(int(id))
	if ((not puzzle == None) and puzzle.answer == request.form['answer']):
		puzzle.tried_num = puzzle.tried_num + 1
		puzzle.passed_num = puzzle.passed_num + 1
		submission = Submission.query.filter_by(user=user.id,puzzle=puzzle.id,accepted=True).first()
		if (submission == None):
			submission = Submission(user=user.id,puzzle=puzzle.id,accepted=True)
			db.session.add(submission)
			db.session.commit()
		return jsonify({"success":True,"correct":True})
	else:
		puzzle.tried_num = puzzle.tried_num + 1
		submission = Submission(user=user.id,puzzle=puzzle.id,accepted=False)
		db.session.add(submission)
		db.session.commit()
		return jsonify({"success":True,"correct":False,"message_header":"再试一次吧","message":"答案不正确"})

@app.route('/login', methods=['POST'])
def login():
	if ('user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=request.form['email']).first()
	if (user == None):
		user = User(email=request.form['email'], nickname=request.form['nickname'],password_hash=hashlib.md5(request.form['password']).hexdigest())
		db.session.add(user)
		session['user'] = user.getData()
	else:
		if (user.verifyPassword(request.form['password'])):
			user.nickname = request.form['nickname']
			session['user'] = user.getData()
		else:
			return "<html><body><script type='text/javascript'>alert('您输入的密码与初设密码不符，验证无法通过！');window.location.href='/';</script></body></html>"
	db.session.commit()
	return redirect(url_for('page_index'))

@app.route('/logout', methods=['GET'])
def logout():
	session.pop('user')
	return redirect(url_for('page_index'))

@app.route('/anonymous', methods=['GET'])
def anonymous():
	user = User(email=''.join(str(uuid.uuid1()).split('-')).upper(), nickname="Anonymous",password_hash="")
	db.session.add(user)
	db.session.commit()
	session['user'] = user.getData()
	return redirect(url_for('page_index'))

@app.route('/puzzle/<id>/rate', methods=['POST'])
def rate(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=session['user']['email']).first()
	mark = Mark.query.filter_by(user=user.id,puzzle=int(id)).first()
	if (mark == None and int(request.form['rating']) > 0 and int(request.form['rating']) <= 5):
		mark = Mark(user=user.id,puzzle=int(id),value=int(request.form['rating']))
		db.session.add(mark)
		db.session.commit()
	return make_response("",200)

@app.route('/puzzle/<id>/next', methods=['GET'])
def next(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	return redirect(url_for('page_puzzle',id=int(id)+1))

@app.route('/puzzle/<id>/hint', methods=['GET'])
def hint(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	if (session['user']['nickname'] == 'Anonymous'):
		return jsonify({"hinttext" : "抱歉，匿名用户无法查看提示，请注册登录后再进行此操作！"})
	user = User.query.filter_by(email=session['user']['email']).first()
	hint = Hint.query.filter_by(user=user.id,puzzle=int(id)).first()
	submission = Submission.query.filter_by(user=user.id,puzzle=id,accepted=True).first()

	if (hint == None and submission == None):
		hint = Hint(user=user.id,puzzle=int(id))
		db.session.add(hint)
		db.session.commit()
	puzzle = Puzzle.query.get(int(id))
	return jsonify({"hinttext" : puzzle.hint})

if __name__ == '__main__':
	app.run(host='0.0.0.0',port=80)
