from datetime import datetime

from django.template import RequestContext
from django.shortcuts import render_to_response, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from models import Category, Page, UserProfile
from forms import CategoryForm, PageForm, UserForm, UserProfileForm
from bing_search import run_query


def index(request):
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)

    # Query the database for a list of ALL categories currently stored
    # Order the categories by no. Likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the List in our context_dict dictionary which will be passed to the template engine.
    category_list = get_category_list()

    most_viewed_page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list,
                    'mostViewedPages': most_viewed_page_list,
    }

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time, "%Y-%m-%d %H:%M:%S.%f")).seconds > 1:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())

    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    return render_to_response('rango/index.html', context_dict, context)


def about(request):
    context = RequestContext(request)
    visits = request.session.get('visits', 1)
    return render_to_response('rango/about.html', {'visits': visits}, context)


@login_required
def like_category(request):
    if request.method == 'GET':
        category_id = request.GET['category_id']

        try:
            category = Category.objects.get(id=category_id)
            category.likes += 1
            category.save()
        except Category.DoesNotExist:
            pass
    else:
        return HttpResponse("Should be POST")

    return HttpResponse(category.likes)


def get_category_list(max_results=0, starts_with=''):
    cat_list = []
    if starts_with:
        cat_list = Category.objects.filter(name__istartswith=starts_with).order_by('-likes')
    else:
        cat_list = Category.objects.all()

    if max_results > 0:
        if len(cat_list) > max_results:
            cat_list = cat_list[:max_results]

    for cat in cat_list:
        cat.url = encode_url(cat.name)
    return cat_list


def suggest_category(request):
    cat_list = []
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']

    cat_list = get_category_list(8, starts_with)
    return render('rango/category_list.html', {'categories': cat_list})


def category(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)
    category_list = get_category_list()

    context_dict = {'category_name': category_name,
                    'category_name_url': category_name_url,
                    'categories': category_list,
    }
    try:
        category = Category.objects.get(name__iexact=category_name)
        pages = Page.objects.filter(category=category).order_by('-views')
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass

    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
            result_list = run_query(query)
            context_dict['result_list'] = result_list

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
        try:
            cat = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            # If we get here, the category does not exist.
            # We render the add_page.html template without a context dictionary.
            # This will trigger the red text to appear in the template!
            return render_to_response('rango/add_page.html', {'category_name': category_name}, context)
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
            return render_to_response('rango/login.html', {'bad_details': True}, context)
    else:
        return render_to_response('rango/login.html', {}, context)


@login_required
def restricted(request):
    context = RequestContext(request)
    return render_to_response('rango/restricted.html', {}, context)


@login_required
def user_logout(request):
    logout(request)

    return HttpResponseRedirect('/rango/')


def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list}, context)


@login_required
def profile(request):
    context = RequestContext(request)
    category_list = get_category_list()
    user_profile = UserProfile.objects.get(user=request.user)

    context_dict = {'user': request.user,
                    'user_profile': user_profile,
                    'categories': category_list,
    }

    return render_to_response('rango/profile.html', context_dict, context)


def track_url(request):
    if request.method == 'GET' and 'page_id' in request.GET:
        page_id = request.GET['page_id']
        try:
            page = Page.objects.get(id=page_id)
        except Page.DoesNotExist:
            return HttpResponseRedirect(reverse('rango:index'))
        page.views += 1
        page.save()
        return HttpResponseRedirect(page.url)

    return HttpResponseRedirect(reverse('rango:index'))