from flask import Flask, request, jsonify, session, make_response, render_template
from google import genai
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid
load_dotenv()

# إنشاء محرك قاعدة البيانات SQLite
engine = create_engine('sqlite:///users.db')

# إنشاء كائن القاعدة الأساسية للإعلان عن النماذج
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    session_id = Column(String)
    prompt =  Column(String)
    response = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now())


# إنشاء الجدول في قاعدة البيانات
Base.metadata.create_all(engine)

# إنشاء جلسة للتعامل مع قاعدة البيانات
Session = sessionmaker(bind=engine)
mysession1 = Session()

def add_row(user_id_arg,session_id,prompt,response):
    mysession1.add(User(user_id=user_id_arg,session_id=session_id,prompt=prompt,response=response))
    mysession1.commit()

app = Flask(__name__)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("لم يتم العثور على مفتاح Gemini API. يرجى تعيين متغير البيئة GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)

def generate_user_id():
    return str(uuid.uuid4())



def get_user_id():
    return request.cookies.get('user_id')

@app.route('/')
def index():
    user_id = request.cookies.get('user_id')
    if user_id:
        return render_template('home_temp.html', title='Chat with Gemini')
    else:
        user_id = generate_user_id()
        res = make_response(render_template('home_temp.html', title='Chat with Gemini'))
        res.set_cookie('user_id', user_id ,max_age=365*24*60*60)
        return res



@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = get_user_id()
        user_message = data.get('message')
        if user_message=='clear' or user_message=='مسح':
            User.query.delete()
        rows = mysession1.query(User).filter(User.user_id==user_id).order_by(User.timestamp.desc()).limit(10).all()
        if rows:
            context = "\n".join([f"User: {conv.prompt}\nAI: {conv.response}" for conv in rows])
            full_prompt = f"{context}\nUser: {user_message}\nAI:"
        else:
            full_prompt = user_message

        print(full_prompt)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt
        )


        new_row = User(
            user_id=user_id,
            session_id=f"session_{user_id}",
            prompt=user_message,
            response=response.text
        )
        mysession1.add(new_row)
        mysession1.commit()

        return jsonify({"response": response.text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "عذرًا، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى."}), 500


if __name__ == '__main__':

    app.run(host='0.0.0.0', debug=True)
