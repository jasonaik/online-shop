from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField


class CreateProductForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    description = CKEditorField("Product Description", validators=[DataRequired()])
    submit = SubmitField("Add Product")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


class ReviewForm(FlaskForm):
    review_text = CKEditorField("Review", validators=[DataRequired()])
    product_rating = SelectField('Product Rating', choices=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                                 validators=[DataRequired()])
    submit = SubmitField("Submit Review")


class UpdateReviewForm(FlaskForm):
    review_text = CKEditorField("Review", validators=[DataRequired()])
    product_rating = SelectField('Product Rating', choices=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                                 validators=[DataRequired()])
    submit = SubmitField("Update Review")