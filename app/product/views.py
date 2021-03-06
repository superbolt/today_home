from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, resolve_url, get_object_or_404, render_to_response
from django.views.generic import ListView, UpdateView, TemplateView

from product.forms import CommentCreateForm, CommentUpdateForm, CommentDeleteForm
from .models import Product, CartItem, Category, Comment

User = get_user_model()


class Home(TemplateView):
    """
    FBV 로 2개의 multiple 한 쿼리셋을 context 에 담아 해당 템플릿으로 렌더링하는 것을
    TemplateView 로 리팩토링하여 재구현
    """
    template_name = 'product/home.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['product_list'] = Product.objects.all()
        context_data['category_list'] = Category.objects.all()
        return context_data


home = Home.as_view()


class CategoryList(TemplateView):
    """
    스토어 > 상품 리스트의 메인 페이지

    body 페이지에는 등록된 모든 상품,
    왼쪽 사이드 바 페이지에는 모든 카테고리를 보여줌
    """
    template_name = 'product/category-list.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['product_list'] = Product.objects.all()
        context_data['category_list'] = Category.objects.all()
        return context_data


category_list = CategoryList.as_view()


def category_detail(request, category_pk):
    """
    store 에서 각 카테고리에 맞는 상품 페이지들을 보여줌
    """
    category_list = Category.objects.all()
    category_detail = Category.objects.get(id=category_pk)
    product_list = Product.objects.filter(category__id=category_detail.id)
    context = {
        'category_list': category_list,
        'category_detail': category_detail,
        'product_list': product_list,
    }
    return render(request, 'product/category-detail.html', context)


def product_detail(request, product_pk):
    product = Product.objects.get(pk=product_pk)
    comment_list = Comment.objects.filter(product__id=product.id)
    context = {
        'product': product,
        'comment_list': comment_list,
    }
    return render(request, 'product/product-detail.html', context)


@login_required
def my_cart(request):
    """
    각 유저의 장바구니 공간
    """
    cart_item = CartItem.objects.filter(user__id=request.user.pk)
    # 장바구니에 담긴 상품의 총 합계 가격
    total_price = 0
    for each_total in cart_item:
        total_price += each_total.product.price * each_total.quantity
    if cart_item is not None:
        context = {
            'cart_item': cart_item,
            'total_price': total_price,
        }
        return render(request, 'cart/cart-list.html', context)
    return redirect('product:my-cart')


@login_required
def add_cart(request, product_pk):
    product = Product.objects.get(pk=product_pk)

    try:
        cart = CartItem.objects.get(product__id=product.pk, user__id=request.user.pk)
        print(cart)
        if cart:
            if cart.product.name == product.name:
                cart.quantity += 1
                cart.save()
                cart_item = CartItem.objects.filter(user__id=request.user.pk)
                print(cart_item)
                print(request.user.pk)
    except CartItem.DoesNotExist:
        user = User.objects.get(pk=request.user.pk)
        cart = CartItem(
            user=user,
            product=product,
            quantity=1,
        )
        cart.save()
        cart_item = CartItem.objects.filter(user__id=request.user.pk)
        print(f'{cart_item} 은 생성되었습니다.')
    # return render(request, 'cart/cart-list.html', {'cart_item': cart_item})
    return redirect('product:my-cart')


def my_cart_item_delete(request, product_pk):
    cart_item = CartItem.objects.filter(product__id=product_pk)
    product = Product.objects.get(pk=product_pk)
    for item in cart_item:
        if item.product.name == product.name:
            item.delete()
        return redirect('product:my-cart')


def minus_cart_item(request, product_pk):
    cart_item = CartItem.objects.filter(product__id=product_pk)
    product = Product.objects.get(pk=product_pk)
    try:
        for item in cart_item:
            if item.product.name == product.name:
                if item.quantity > 1:
                    item.quantity -= 1
                    item.save()
                return redirect('product:my-cart')
            else:
                # messages 는 현재 동작하지 않음(form 을 통해 message 를 띄우기 때문에 기능은 보류 상태)
                messages.error(request, '장바구니의 최소 수량은 1개입니다.', extra_tags='alert')
                return redirect('product:my-cart')
    except CartItem.DoesNotExist:
        raise Http404


def plus_cart_item(request, product_pk):
    cart_item = CartItem.objects.filter(product__id=product_pk)
    product = Product.objects.get(pk=product_pk)
    try:
        for item in cart_item:
            if item.product.name == product.name:
                if item.quantity:
                    item.quantity += 1
                    item.save()
                return redirect('product:my-cart')
            # else:
            #     # messages 는 현재 동작하지 않음(form 을 통해 message 를 띄우기 때문에 기능은 보류 상태)
            #     messages.error(request, '장바구니의 최소 수량은 1개입니다.', extra_tags='alert')
            #     return redirect('product:my-cart')
    except CartItem.DoesNotExist:
        raise Http404


def comment_create(request, product_pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_pk)
        form = CommentCreateForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content = form.cleaned_data['content']
            comment.rating = form.cleaned_data['rating']
            comment.image = form.cleaned_data['image']
            comment.product = product
            form.save()
            # messages.success(request, '댓글이 생성되었습니다.')
            return redirect('product:product-detail', product.pk)

    form = CommentCreateForm()
    context = {
        'form': form,
    }
    return render(request, 'product/comment-create.html', context)


# class CommentUpdateView(UpdateView):
#     model = Comment
#     fields = ['rating', 'content', 'image']
#
#     def get_object(self, *args, **kwargs):
#         obj = super(CommentUpdateView, self).get_object(*args, **kwargs)
#         if not obj.user == self.request.user:
#             raise Http404
#         return obj
#
#     def form_valid(self, form):
#         form.instance.user = self.request.user
#         return super(CommentUpdateView, self).form_valid(form)
#
#     def get_success_url(self):
#         # Product 모델에서 get_absolute_url 로 reverse 경로를 지정해야
#         # get_success_url 함수가 동작
#         return resolve_url(self.object.product)
#
#
# comment_edit = CommentUpdateView.as_view()


@login_required
def comment_edit(request, product_pk, pk):
    product = get_object_or_404(Product, pk=product_pk)
    # Comment 객체 하나를 가져와야 하기 때문에 Comment 모델에서 출발
    comment = Comment.objects.get(pk=pk)
    if request.user.id == comment.user.id:
        if request.method == 'POST':
            form = CommentUpdateForm(request.POST, request.FILES, instance=comment)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.content = form.cleaned_data['content']
                comment.rating = form.cleaned_data['rating']
                comment.image = form.cleaned_data['image']
                form.save()
                messages.info(request, '{} 님이 작성하신 댓글 수정이 완료되었습니다. :-)'.format(request.user.name))
                return redirect('product:product-detail', comment.product.pk)
        form = CommentUpdateForm(instance=comment)
        context = {
            'form': form,
        }
        return render(request, 'product/comment_form.html', context)

    messages.info(request, '[{}] 님이 작성하신 댓글이 아니에요. :-)'.format(request.user.name))
    return redirect('product:product-detail', comment.product.pk)


@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    product = Product.objects.get(pk=comment.product.id)

    # 댓글 작성자가 현재 로그인한 유저와 같을 때 get 요청으로 form 을 받고,
    #   이후 post 로 form 을 받아 comment 인스턴스를 삭제
    if comment.user.pk == request.user.pk:
        if request.method == 'POST':
            comment.delete()
            messages.info(request, '댓글이 삭제되었습니다.')
            return redirect('product:product-detail', product.id)
        form = CommentDeleteForm()
        context = {
            'form': form,
        }
        return render(request, 'product/comment_confirm_delete.html', context)
    # 댓글 작성자가 아닐 경우 messages 를 띄우고 해당 상품 상세 페이지 redirect()
    messages.info(request, '댓글 작성자가 아닙니다.')
    return redirect('product:product-detail', product.id)


class SearchListView(ListView):
    model = Product
    queryset = Product.objects.all()
    template_name = 'product/category-list.html'

    def get_queryset(self):
        self.q = self.request.GET.get('q', '')

        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
            print(qs)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.q
        return context
