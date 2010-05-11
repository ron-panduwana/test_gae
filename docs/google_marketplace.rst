Google Marketplace Integration
==============================

General layout of the *Google Marketplace* integration and application lifecycle
is presented in the document
`Application Lifecycle
<http://code.google.com/intl/pl/googleapps/marketplace/lifecycle.html>`_.

The main lifecycle stages are:

* `Installation`_

  * Present Terms Of Services
  * `Grant Data Access`_
  * (Optional) `Application-specific Configuration`_
  * Enable

* `End-user Daily Use`_
* Domain Administrator Additional Configuration
* Application Disablement
* Application Deletion

The above steps will be now described in the context of *Powerpanel* application.

Installation
************

All of the details of the *Google Marketplace* integration are implemented by
the :doc:`../crauth/index` package.

General behavior during the installation process (and afterwards) is controlled
by the ``manifest.xml`` file uploaded to the *Google Marketplace* during the
creation of application listing. Structure and contents of this file are
described in
`Application Manifest
<http://code.google.com/intl/pl/googleapps/marketplace/manifest.html>`_
document.

To simplify creation of ``manifest.xml`` files a
:func:`crauth.views.generate_manifest` view was created. It is accessbile at::

   /openid/__manifest/

(which is accessbile only to the application developers/administrators) and
returns ``manifest.xml`` file ready to be uploaded.

Sample ``manifest.xml`` file may look like this:

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8" ?>
   <ApplicationManifest xmlns="http://schemas.google.com/ApplicationManifest/2009">
     <Name></Name>
     <Description></Description>
   
     <!-- Administrators and users will be sent to this URL for application support -->
     <Support>
       
       <Link rel="setup" href="http://kamil.latest.ga-powerpanel-dev.appspot.com/openid/setup/${DOMAIN_NAME}/"/>
     </Support>
   
     <!-- Show this link in Google's universal navigation for all users -->
     <Extension id="navLink" type="link">
       <Name></Name>
       <Url>http://kamil.latest.ga-powerpanel-dev.appspot.com/openid/login/${DOMAIN_NAME}/?from=google</Url>
       <Scope ref="provisioningAPI"/>
     </Extension>
   
     <!-- Declare our OpenID realm so our app is white listed -->
     <Extension id="realm" type="openIdRealm">
       <Url>http://kamil.latest.ga-powerpanel-dev.appspot.com/</Url>
     </Extension>
   
     <Scope id="provisioningAPI">
       <Url>https://apps-apis.google.com/a/feeds/user/#readonly</Url>
       <Reason>This app manages domain user accounts.</Reason>
     </Scope>
   </ApplicationManifest>


Grant Data Access
-----------------

Each application has to specify which GData APIs
it wants to use with OAuth two-legged authentication in the
``manifest.xml`` file. *Powerpanel* currently only specifies
`Provisioning API <http://code.google.com/intl/pl/googleapps/domain/gdata_provisioning_api_v2.0_developers_protocol.html>`_
there as it needs to find out if the user accessing
:func:`crauth.views.domain_setup` view is domain administrator.

.. note::

   Provisioning API is currently **read-only** when accessed using OAuth
   two-legged authentication.

Application-specific Configuration
----------------------------------

This is optional, but is used by *Powerpanel* for initial configuration of
the domain credentials (domain administrator email address and password).
This step is handled by :func:`crauth.views.domain_setup` view.


End-user Daily Use
******************

The most important aspect of the *Google Marketplace* integration is the
improved user-experience for end-users. Installed applications are linked
on the *Google Apps* base application (like *GMail*, *Docs*, etc.).
Moreover, users don't have to log in to the *Powerpanel* manually, as this
step is removed altogether thanks to
`Single Sign-On <http://code.google.com/intl/pl/googleapps/marketplace/sso.html>`_.

*Single Sign-On* in the context of *Google Marketplace* is based on *OpenID*
standard. To integrate it with the *Powerpanel* application we used
`python-openid <http://openidenabled.com/python-openid/>`_ library.

Unfortunately the OpenID discovery mechanism for *Google Apps* endpoints is
slightly different than standard OpenID one we had implemenent this step
ourselves. It is described in the
`Google Federated Login API <http://groups.google.com/group/google-federated-login-api/web/openid-discovery-for-hosted-domains?pli=1>`_
document and implemented by :mod:`crauth.ga_openid` module. Details are
described :ref:`below <single-sign-on>`.

.. _single-sign-on:

Single Sign-On/OpenID authentication
------------------------------------

When user clicks the *Powerpanel* link in his *Google Apps* dashboard he is
redirected to the URL of form::

   /openid/login/example.com/?from=google

(provided his *Google Apps* domain is ``example.com``). This address is handled
by the :func:`crauth.views.openid_start` view. This view then performs the
following steps:

* Call :func:`crauth.models.AppsDomain.is_arbitrary_domain_active` to check
  if ``example.com`` is licensed to use *Powerpanel*. If it's not the user
  is shown proper error message.
* Call :func:`crauth.ga_openid.discover_google_apps` to perform actual
  *Google Apps*-specific OpenID endpoint discovery. This step in turn consists
  of the following substeps:

  * Fetch host-meta file from::

       https://www.google.com/accounts/o8/.well-known/host-meta?hd=example.com

  * This host-meta file points to an *XRDS* which describes host-wide
    meta-data.
  * This *XRDS* file is then fetched. It is signed with the certificate which
    is embedded in the *XRDS* file itself. It is important to verify that
    the signature is correct (i.e. the file was signed using embedded certificate)
    and that the certificate itself is issues (i.e. signed) by proper authority.
    In this case embedded certificate should be signed by
    `GoogleInternatAuthority.crt
    <http://www.gstatic.com/GoogleInternetAuthority/GoogleInternetAuthority.crt>`_
    (which is stored in the repository at ``crauth/GoogleInternetAuthority.crt``).
    Of course, it is also needed to verify that ``GoogleInternetAuthority.crt``
    is issued by proper Certification Authority, but
    this step may be performed offline (e.g. using *OpenSSL* software). It may
    easily be done with::

       python manage.py check_cafile

    Details of the above process are implemented in
    :func:`crauth.ga_openid._fetch_xrds` and use
    `TLS lite <http://trevp.net/tlslite/>`_ library internally.

  * After the authenticity of the *XRDS* file is verified it is used to create
    :class:`openid.consumer.discover.OpenIDServiceEndpoint` object. This
    object is returned from :func:`crauth.ga_openid.discover_google_apps`.

* From this point the normal *python-openid* functionality is used, i.e.:

  * :func:`openid.consumer.consumer.Consumer.beginWithoutDiscovery` is called
    to begin the OpenID authentication process.
  * Additional properties (email and full_name) of the user are requested using
    `OpenID Attribute Exchange
    <http://openid.net/specs/openid-attribute-exchange-1_0.html>`_
    extension.
  * User is redirected to the URL constructed by the
    :class:`openid.consumer.consumer.Consumer` object. This URL points to
    *Google* servers. If the user is already logged in to the *Google Apps*
    domain he will simply be redirected back to *Powerpanel*. If he's not
    he will simply have to login to his *Google Apps* account via usual
    mechanism and then he will be redirected to *Powerpanel*.
  * When user is redirected to *Powerpanel* he lands at::

       /openid/return/

    address which is handled by :func:`crauth.views.openid_return` view.
    It simply checks that data returned by *Google* is correct and then
    stores information about successful login in the user cookie. From this
    moment on the user is logged in to the *Powerpanel* application.

If given view is to only be accessed by logged in users it may use
:func:`crauth.decorators.login_required` decorator, e.g.:

.. code-block:: python

   from crauth.decorators import login_required

   @login_required
   def some_view(request):
       pass

If such view is accessed by unauthenticated user, the above OpenID
authentication process will be first performed and then the user will come
back to this view.

OpenID authentication for manually-managed domains
--------------------------------------------------

Because we're currently in the pre-beta state, *Powerpanel* application
is not publicly visible in the *Google Marketplace* listings and so
it cannot be easily installed by customers. If it's not installed,
the *Licensing API* will return ``UNLICENSED`` state for the domain.

Therefore we have to support manual managing of domains before *Powerpanel*
is submitted and approved by *Google Powerpanel*. This situation is handled
by :func:`crauth.models.AppsDomain.is_active` method. The
:class:`crauth.models.AppsDomain` instances have the following attributes which
control whether given domain is allowed to use the application:

* :attr:`is_enabled <crauth.models.AppsDomain.is_enabled>`,
* :attr:`license_state <crauth.models.AppsDomain.license_state>`,
* :attr:`is_independent <crauth.models.AppsDomain.is_independent>`.

The most important on is :attr:`is_enabled <crauth.models.AppsDomain.is_enabled>`.
If it's set to ``False`` the domain is not allowed to use the domain regardless
of the remaining attributes. If it's set to ``True``, the domain is allowed
the application if the following Python condition is met:

.. code-block:: python
   
   is_independent or license_state == STATE_ACTIVE

Which means that if :attr:`is_independent <crauth.models.AppsDomain.is_independent>`
is set to ``True`` the license state is ignored altogether.

.. note::

   Manually-managed domains, whose license state is not :const:`STATE_ACTIVE`
   will require additional step during the OpenID authentication process.
   The user will be prompted to grant access to his email address and name
   details and only then redirected back to *Powerpanel*.

