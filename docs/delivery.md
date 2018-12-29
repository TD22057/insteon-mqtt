# Creating a delivery

- Start on the development branch

  ```
  git checkout dev
  ```

- Update the version number.  Versions numbers have the format
  major.minor.patch so pass the string of the number you want to update to
  bumpversion.

  ```
  bumpversion --verbose patch
  ```

  This will update all the files on the dev branch to the new version and
  submit them.  Push the update to github.

  `git push`

- Merge code from the development branch to to the main branch.

   ```
   git checkout master
   git merge --no-ff dev
   git push
   ```

- Update the docker images.  The repository location is linked to a user name
  (TD22057) so in this case, only the repository owner can update the docker
  images.

  ```
  docker login
  ./scripts/docker-create.sh
  ```
