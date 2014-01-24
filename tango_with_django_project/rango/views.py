from django.template import RequestContext
from django.shortcuts import render_to_response
from models import Category, Page
from forms import CategoryForm


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
        category.url = category_name_to_url(category.name)

    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    return render_to_response('rango/index.html', context_dict, context)


def about(request):
    context = RequestContext(request)
    return render_to_response('rango/about.html', context)


def category(request, category_name_url):
    context = RequestContext(request)
    category_name = url_to_category_name(category_name_url)
    context_dict = {'category_name': category_name}

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass

    return render_to_response('rango/category.html', context_dict, context)


def category_name_to_url(category_name):
    return category_name.replace(' ', '_')


def url_to_category_name(url):
    return url.replace('_', ' ')


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