from datetime import datetime

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required

from models import Category, Page
from forms import CategoryForm, PageForm, UserForm, UserProfileForm


def index(request):
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)

    # Query the database for a list of ALL categories currently stored
    # Order the categories by no. Likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the List in our context_dict dictionary which will be passed to the template engine.
    category_list = Category.objects.order_by('-likes')[:5]
    mostViewedPage_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list,
                    'mostViewedPages': mostViewedPage_list,
    }

    for category in category_list:
        category.url = encode_url(category.name)

    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    response = render_to_response('rango/index.html', context_dict, context)

    visits = int(request.COOKIES.get('visits', '1'))

    # Does the cookie last_visit exist?
    if request.COOKIES.has_key('last_visit'):
        # Yes it does! Get the cookie's value.
        last_visit = request.COOKIES['last_visit']
        # Cast the value to a Python date/time object.
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

        # If it's been more than a day since the last visit...
        if (datetime.now() - last_visit_time).days > 0:
            # ...reassign the value of the cookie to +1 of what it was before...
            response.set_cookie('visits', visits + 1)
            # ...and update the last visit cookie, too.
            response.set_cookie('last_visit', datetime.now())
    else:
        # Cookie last_visit doesn't exist, so create it to the current date/time.
        response.set_cookie('last_visit', datetime.now())


    # Return response back to the user, updating any cookies that need changed.
    return response


def about(request):
    context = RequestContext(request)
    return render_to_response('rango/about.html', {}, context)


def category(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)
    context_dict = {'category_name': category_name,
                    'category_name_url': category_name_url}

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass

    return render_to_response('rango/category.html', context_dict, context)


def encode_url(category_name):
    return category_name.replace(' ', '_')


def decode_url(url):
    return url.replace('_', ' ')


@login_required
def add_category(request):
    # Get the context from the request.
    context = RequestContext(request)

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render_to_response('rango/add_category.html', {'form': form}, context)


@login_required
def add_page(request, category_name_url):
    context = RequestContext(request)

    category_name = decode_url(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            # This time we cannot commit straight away.
            # Not all fields are automatically populated!
            page = form.save(commit=False)

            # Retrieve the associated Category object so we can add it.
            # Wrap the code in a try block - check if the category actually exists!
            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                # If we get here, the category does not exist.
                # We render the add_page.html template without a context dictionary.
                # This will trigger the red text to appear in the template!
                return render_to_response('rango/add_page.html', {'category_name': category_name}, context)

            # Also, create a default value for the number of views.
            page.views = 0

            # With this, we can then save our new model instance.
            page.save()

            # Now that the page is saved, display the category instead.
            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html',
                              {'category_name_url': category_name_url,
                               'category_name': category_name, 'form': form},
                              context)


def register(request):
    context = RequestContext(request)

    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()

            registered = True

        else:
            print user_form.errors, profile_form.errors

    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response(
        'rango/register.html',
        {'user_form': user_form, 'profile_form': profile_form, 'registered': registered},
        context
    )


def user_login(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                return HttpResponse("Your Rango account is disabled.")
        else:
            print "Invalid login details: {0}, {1}".format(username, password)
            return render_to_response('rango/login.html', {'loginFailure_message': "Invalid login details"}, context)
    else:
        return render_to_response('rango/login.html', {}, context)


@login_required
def restricted(request):
    return render_to_response('rango/restricted.html', {}, context)


@login_required
def user_logout(request):
    logout(request)

    return HttpResponseRedirect('/rango/')